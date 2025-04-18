import asyncio
import os
import tempfile
import time
from dotenv import load_dotenv

from playwright.async_api import async_playwright as playwright
from playwright.async_api import BrowserContext
from playwright.async_api import Page
from playwright.async_api import Playwright

from core.utils.notification import NotificationManager
from core.utils.ui_manager import UIManager
from core.utils.dom_mutation_observer import dom_mutation_change_detected
from core.utils.dom_mutation_observer import handle_navigation_for_mutation_observer
from core.utils.js_helper import beautify_plan_message
from core.utils.js_helper import escape_js_message
from core.utils.logger import logger
from core.utils.message_type import MessageType
import logfire

load_dotenv()

# Enusres that playwright does not wait for font loading when taking screenshots. Reference: https://github.com/microsoft/playwright/issues/28995
os.environ["PW_TEST_SCREENSHOT_NO_FONTS_READY"] = "1"

class PlaywrightManager:
    """
    A singleton class to manage Playwright instances and browsers.

    Attributes:
        browser_type (str): The type of browser to use ('chromium', 'firefox', 'webkit').
        isheadless (bool): Flag to launch the browser in headless mode or not.

    The class ensures only one instance of itself, Playwright, and the browser is created during the application lifecycle.
    """
    _homepage = "https://www.google.com"
    _instance = None
    _playwright = None # type: ignore
    _browser_context = None
    __async_initialize_done = False
    _take_screenshots = False
    _screenshots_dir = None
    video_dir = os.path.join(os.getcwd(), "videos")
    _record_video = True
    _browser = None


    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)


    def __init__(self, 
                 browser_type: str = "chromium", 
                 headless: bool = False, 
                 gui_input_mode: bool = True, 
                 screenshots_dir: str = "", 
                 take_screenshots: bool = True, 
                 video_dir: str = os.path.join(os.getcwd(), "videos"), 
                 record_video: bool = True,
                ):
        """
        Initializes the PlaywrightManager with the specified browser type and headless mode.
        Initialization occurs only once due to the singleton pattern.

        Args:
            browser_type (str, optional): The type of browser to use. Defaults to "chromium".
            headless (bool, optional): Flag to launch browser in headless mode. Defaults to False.
            gui_input_mode (bool, optional): Enable GUI input mode. Defaults to True.
            screenshots_dir (str, optional): Directory for screenshots. Defaults to "".
            take_screenshots (bool, optional): Enable screenshot taking. Defaults to False.
            video_dir (str, optional): Directory for video recording. Defaults to "videos" in current dir.
            record_video (bool, optional): Enable video recording. Defaults to True.
        """
        self.browser_type = browser_type
        self.isheadless = headless
        self.notification_manager = NotificationManager()
        self.user_response_event = asyncio.Event()
        self.ui_manager = None
        if gui_input_mode:
            self.ui_manager: UIManager = UIManager()

        self.set_take_screenshots(take_screenshots)
        self.set_screenshots_dir(screenshots_dir)
        self.set_video_recording(record_video)
        self.set_video_dir(video_dir)

    def set_video_recording(self, record_video: bool):
        self._record_video = record_video

    def get_video_recording(self):
        return self._record_video
    
    def set_video_dir(self, video_dir: str):
        self._video_dir = video_dir
    
    def get_video_dir(self):
        return self._video_dir


    async def async_initialize(self):
        """
        Asynchronously initialize necessary components and handlers for the browser context.
        """
        if self.__async_initialize_done:
            return

        # Step 1: Ensure Playwright is started and browser context is created
        await self.start_playwright()
        await self.ensure_browser_context()

        # Step 2: Deferred setup of handlers
        await self.setup_handlers()

        # Step 3: Navigate to homepage
        await self.go_to_homepage()

        self.__async_initialize_done = True


    async def ensure_browser_context(self):
        """
        Ensure that a browser context exists, creating it if necessary.
        """
        if self._browser_context is None:
            await self.create_browser_context()


    async def setup_handlers(self):
        """
        Setup various handlers after the browser context has been ensured.
        """
        if not self.ui_manager:
            return
        await self.set_overlay_state_handler()
        await self.set_user_response_handler()
        await self.set_navigation_handler()


    async def start_playwright(self):
        """
        Starts the Playwright instance if it hasn't been started yet. This method is idempotent.
        """
        if not PlaywrightManager._playwright:
            PlaywrightManager._playwright: Playwright = await playwright().start()


    async def stop_playwright(self):
        """
        Stops the Playwright instance and resets it to None. This method should be called to clean up resources.
        """
        if self._record_video and self._browser_context:
            logger.info("Stopping video recording and closing pages...")
            for page in self._browser_context.pages:
                await page.close()  # This triggers saving the video

        # Close the browser context if it's initialized
        if PlaywrightManager._browser_context is not None:
            await PlaywrightManager._browser_context.close()
            PlaywrightManager._browser_context = None

        # Stop the Playwright instance if it's initialized
        if PlaywrightManager._playwright is not None: # type: ignore
            await PlaywrightManager._playwright.stop()
            PlaywrightManager._playwright = None # type: ignore

    
    async def navigate_to_url(self, url: str):
        """Navigate to the specified URL"""
        try:
            # Add URL protocol if missing
            url = "https://" + url if not url.startswith(('http://', 'https://')) else url
            page = await self.get_current_page()
            await page.goto(url)
            logger.info(f"Successfully navigated to {url}")
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {str(e)}")
            raise


    async def create_browser_context(self):
        """
        Creates a new browser context using the specified or default browser directory.
        """
        user_dir:str = os.environ.get('BROWSER_STORAGE_DIR', '')
        steel_api_key = os.environ.get('STEEL_DEV_API_KEY')
        record_video_options = {}
        logger.info(f"Video dir: {self.video_dir}, record_video: {self._record_video}")
    
        if self._record_video and self._video_dir:
            os.makedirs(self._video_dir, exist_ok=True)
            record_video_options = {
                "record_video_dir": self._video_dir,
                "record_video_size": {"width": 640, "height": 480}
            }
            logger.info("Video recording enabled with options:", extra={"video_options": record_video_options})


        if self.browser_type == "chromium":
            logger.info(f"User dir: {user_dir}")
            try:
                if steel_api_key:
                # Try CDP connection first if API key exists
                    try:
                        logger.info("Attempting CDP connection with Steel Dev...")
                        PlaywrightManager._browser = await PlaywrightManager._playwright.chromium.connect_over_cdp(
                            f'wss://connect.steel.dev?apiKey={steel_api_key}'
                        )
                        PlaywrightManager._browser_context = PlaywrightManager._browser.contexts[0]
                        return
                    except Exception as cdp_error:
                        logger.warning(f"CDP connection failed, falling back to local browser: {cdp_error}")

                logger.warning("Falling back to local browser with new user dir")

                #Fall back to local browser launch if CDP fails or no API key
                PlaywrightManager._browser_context = await PlaywrightManager._playwright.chromium.launch_persistent_context(
                    user_dir,
                    bypass_csp=True,
                    channel="chromium", headless=self.isheadless,
                    args=["--disable-blink-features=AutomationControlled",
                        "--disable-session-crashed-bubble",  # disable the restore session bubble
                        "--disable-infobars",  # disable informational popups,
                        ],
                    no_viewport=True,
                    **record_video_options,
                )
            except Exception as e:
                if "Target page, context or browser has been closed" in str(e):
                    new_user_dir = tempfile.mkdtemp()
                    logger.error(f"Failed to launch with {user_dir}, trying new dir {new_user_dir}")
                    
                    if steel_api_key:
                        # Try CDP one more time with new user dir
                        try:
                            PlaywrightManager._browser = await PlaywrightManager._playwright.chromium.connect_over_cdp(
                                f'wss://connect.steel.dev?apiKey={steel_api_key}'
                            )
                            PlaywrightManager._browser_context = PlaywrightManager._browser.contexts[0]
                            return
                        except Exception as cdp_error:
                            logger.warning(f"CDP connection failed, falling back to local browser: {cdp_error}")

                    logger.warning("Falling back to local browser with new user dir")
                    # Fall back to local browser with new user dir
                    PlaywrightManager._browser_context = await PlaywrightManager._playwright.chromium.launch_persistent_context(
                        new_user_dir,
                        channel="chromium",
                        headless=self.isheadless,
                        args=["--disable-blink-features=AutomationControlled",
                            "--disable-session-crashed-bubble",
                            "--disable-infobars"],
                        no_viewport=True,
                        **record_video_options,
                    )
                elif "Chromium distribution 'chromium' is not found" in str(e):
                    raise ValueError("Chromium not installed. Install Google chromium or run 'playwright install chromium'") from None
                else:
                    raise e from None
        else:
            raise ValueError(f"Unsupported browser type: {self.browser_type}")


    async def get_browser_context(self):
            """
            Returns the existing browser context, or creates a new one if it doesn't exist.
            """
            await self.ensure_browser_context()
            return self._browser_context


    async def get_current_url(self) -> str | None:
        """
        Get the current URL of current page

        Returns:
            str | None: The current URL if any.
        """
        try:
            current_page: Page =await self.get_current_page()
            return current_page.url
        except Exception:
            pass
        return None

    async def get_current_page(self) -> Page :
        """
        Get the current page of the browser

        Returns:
            Page: The current page if any.
        """
        try:
            browser: BrowserContext = await self.get_browser_context() # type: ignore
            # Filter out closed pages
            pages: list[Page] = [page for page in browser.pages if not page.is_closed()]
            page: Page | None = pages[-1] if pages else None
            logger.debug(f"Current page: {page.url if page else None}")
            if page is not None:
                return page
            else:
                page:Page = await browser.new_page() # type: ignore
                return page
        except Exception:
                logger.warn("Browser context was closed. Creating a new one.")
                PlaywrightManager._browser_context = None
                _browser:BrowserContext= await self.get_browser_context() # type: ignore
                page: Page | None = await self.get_current_page()
                return page


    async def close_all_tabs(self, keep_first_tab: bool = True):
            """
            Closes all tabs in the browser context, except for the first tab if `keep_first_tab` is set to True.

            Args:
                keep_first_tab (bool, optional): Whether to keep the first tab open. Defaults to True.
            """
            browser_context = await self.get_browser_context()
            pages: list[Page] = browser_context.pages #type: ignore
            pages_to_close: list[Page] = pages[1:] if keep_first_tab else pages # type: ignore
            for page in pages_to_close: # type: ignore
                await page.close() # type: ignore


    async def close_except_specified_tab(self, page_to_keep: Page):
        """
        Closes all tabs in the browser context, except for the specified tab.

        Args:
            page_to_keep (Page): The Playwright page object representing the tab that should remain open.
        """
        browser_context = await self.get_browser_context()
        for page in browser_context.pages: # type: ignore
            if page != page_to_keep:  # Check if the current page is not the one to keep
                await page.close() # type: ignore


    async def go_to_homepage(self):
        await self.navigate_to_url(self._homepage)


    async def set_navigation_handler(self):
        page:Page = await PlaywrightManager.get_current_page(self)
        page.on("domcontentloaded", self.ui_manager.handle_navigation) # type: ignore
        page.on("domcontentloaded", handle_navigation_for_mutation_observer) # type: ignore
        await page.expose_function("dom_mutation_change_detected", dom_mutation_change_detected) # type: ignore

    async def set_overlay_state_handler(self):
        logger.debug("Setting overlay state handler")
        context = await self.get_browser_context()
        await context.expose_function('overlay_state_changed', self.overlay_state_handler) # type: ignore
        await context.expose_function('show_steps_state_changed',self.show_steps_state_handler) # type: ignore

    async def overlay_state_handler(self, is_collapsed: bool):
        page = await self.get_current_page()
        self.ui_manager.update_overlay_state(is_collapsed)
        if not is_collapsed:
            await self.ui_manager.update_overlay_chat_history(page)

    async def show_steps_state_handler(self, show_details: bool):
        page = await self.get_current_page()
        await self.ui_manager.update_overlay_show_details(show_details, page)

    async def set_user_response_handler(self):
        context = await self.get_browser_context()
        await context.expose_function('user_response', self.receive_user_response) # type: ignore


    async def notify_user(self, message: str, message_type: MessageType = MessageType.STEP):
        """
        Notify the user with a message.

        Args:
            message (str): The message to notify the user with.
            message_type (enum, optional): Values can be 'PLAN', 'QUESTION', 'ANSWER', 'INFO', 'STEP'. Defaults to 'STEP'.
            To Do: Convert to Enum.
        """
        if not self.ui_manager:
            return
        logfire.info(f"Notify user with message: {message}")
        logfire.info(f"Message type: {message_type}")

        if message.startswith(":"):
            message = message[1:]

        if message.endswith(","):
            message = message[:-1]

        if message_type == MessageType.PLAN:
            message = beautify_plan_message(message)
            message = "Plan:\n" + message
        elif message_type == MessageType.STEP:
            if "confirm" in message.lower():
                message = "Verify: " + message
            else:
                message = "Next step: " + message
        elif message_type == MessageType.QUESTION:
            message = "Question: " + message
        elif message_type == MessageType.ANSWER:
            message = "Response: " + message

        safe_message = escape_js_message(message)
        self.ui_manager.new_system_message(safe_message, message_type)

        if self.ui_manager.overlay_show_details == False:  # noqa: E712
            if message_type not in (MessageType.PLAN, MessageType.QUESTION, MessageType.ANSWER, MessageType.INFO):
                return

        if self.ui_manager.overlay_show_details == True:  # noqa: E712
            if message_type not in (MessageType.PLAN,  MessageType.QUESTION , MessageType.ANSWER,  MessageType.INFO, MessageType.STEP):
                return

        safe_message_type = escape_js_message(message_type.value)
        try:
            js_code = f"addSystemMessage({safe_message}, is_awaiting_user_response=false, message_type={safe_message_type});"
            page = await self.get_current_page()
            await page.evaluate(js_code)
        except Exception as e:
            logger.error(f"Failed to notify user with message \"{message}\". However, most likey this will work itself out after the page loads: {e}")

        self.notification_manager.notify(message, message_type.value)

    async def highlight_element(self, selector: str, add_highlight: bool):
        try:
            page: Page = await self.get_current_page()
            if add_highlight:
                # Add the 'tawebagent-ui-automation-highlight' class to the element. This class is used to apply the fading border.
                await page.eval_on_selector(selector, '''e => {
                            let originalBorderStyle = e.style.border;
                            e.classList.add('tawebagent-ui-automation-highlight');
                            e.addEventListener('animationend', () => {
                                e.classList.remove('tawebagent-ui-automation-highlight')
                            });}''')
                logger.debug(f"Applied pulsating border to element with selector {selector} to indicate text entry operation")
            else:
                # Remove the 'tawebagent-ui-automation-highlight' class from the element.
                await page.eval_on_selector(selector, "e => e.classList.remove('tawebagent-ui-automation-highlight')")
                logger.debug(f"Removed pulsating border from element with selector {selector} after text entry operation")
        except Exception:
            # This is not significant enough to fail the operation
            pass

    async def receive_user_response(self, response: str):
        self.user_response = response  # Store the response for later use.
        logger.debug(f"Received user response to system prompt: {response}")
        # Notify event loop that the user's response has been received.
        self.user_response_event.set()


    async def prompt_user(self, message: str) -> str:
        """
        Prompt the user with a message and wait for a response.

        Args:
            message (str): The message to prompt the user with.

        Returns:
            str: The user's response.
        """
        if not self.ui_manager:
            return
        logger.debug(f"Prompting user with message: \"{message}\"")
        #self.ui_manager.new_system_message(message)

        page = await self.get_current_page()

        await self.ui_manager.show_overlay(page)
        self.log_system_message(message, MessageType.QUESTION) # add the message to history after the overlay is opened to avoid double adding it. add_system_message below will add it

        safe_message = escape_js_message(message)

        js_code = f"addSystemMessage({safe_message}, is_awaiting_user_response=true, message_type='question');"
        await page.evaluate(js_code)

        await self.user_response_event.wait()
        result = self.user_response
        logger.info(f"User prompt reponse to \"{message}\": {result}")
        self.user_response_event.clear()
        self.user_response = ""
        self.ui_manager.new_user_message(result)
        return result

    def set_take_screenshots(self, take_screenshots: bool):
        self._take_screenshots = take_screenshots

    def get_take_screenshots(self):
        return self._take_screenshots

    def set_screenshots_dir(self, screenshots_dir: str):
        """
        Set the directory for saving screenshots, creating it if it doesn't exist.
        
        Args:
            screenshots_dir (str): Path to the screenshots directory
        """
        if not screenshots_dir:
            # If no directory specified, create a 'screenshots' directory in current working directory
            screenshots_dir = os.path.join(os.getcwd(), "screenshots")
        
        # Ensure the path is absolute
        screenshots_dir = os.path.abspath(screenshots_dir)
        
        # Create the directory if it doesn't exist
        os.makedirs(screenshots_dir, exist_ok=True)
        
        self._screenshots_dir = screenshots_dir
        logger.debug(f"Screenshots directory set to: {screenshots_dir}")



    def get_screenshots_dir(self):
        return self._screenshots_dir

    async def take_screenshots(self, name: str, page: Page|None, full_page: bool = True, 
                         include_timestamp: bool = True, load_state: str = 'domcontentloaded', 
                         take_snapshot_timeout: int = 15*1000):
        if not self._take_screenshots or not self._screenshots_dir:
            return
            
        if page is None:
            page = await self.get_current_page()

        screenshot_name = name
        if include_timestamp:
            screenshot_name = f"{int(time.time_ns())}_{screenshot_name}"
        screenshot_name += ".png"
        
        # Use os.path.join to create proper path
        screenshot_path = os.path.join(self._screenshots_dir, screenshot_name)
        
        try:
            await page.wait_for_load_state(state=load_state, timeout=take_snapshot_timeout)
            await page.screenshot(path=screenshot_path, full_page=full_page, 
                                timeout=take_snapshot_timeout, caret="initial", scale="device")
            logger.debug(f"Screenshot saved to: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"Failed to take screenshot and save to \"{screenshot_path}\". Error: {e}")
            return None


    def log_user_message(self, message: str):
        """
        Log the user's message.

        Args:
            message (str): The user's message to log.
        """
        if not self.ui_manager:
            return
        self.ui_manager.new_user_message(message)


    def log_system_message(self, message: str, type: MessageType = MessageType.STEP):
        """
        Log a system message.

        Args:
            message (str): The system message to log.
        """
        self.ui_manager.new_system_message(message, type)

    async def update_processing_state(self, processing_state: str):
        """
        Update the processing state of the overlay.

        Args:
            is_processing (str): "init", "processing", "done"
        """
        if not self.ui_manager:
            return
        page = await self.get_current_page()

        await self.ui_manager.update_processing_state(processing_state, page)

    async def command_completed(self, command: str, elapsed_time: float | None = None):
        """
        Notify the overlay that the command has been completed.
        """
        logger.debug(f"Command \"{command}\" has been completed. Focusing on the overlay input if it is open.")
        page = await self.get_current_page()
        await self.ui_manager.command_completed(page, command, elapsed_time)