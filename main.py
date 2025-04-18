from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from scraper import scrape_tesco_beer_deals

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head><title>Booze News 🧃</title></head>
        <body>
            <h1>🍻 Booze News: Find Beer Deals</h1>
            <form action="/run" method="get">
                <label for="prompt">Search Prompt:</label><br>
                <input type="text" id="prompt" name="prompt" value="Find beer deals in UK supermarkets"><br><br>
                <input type="submit" value="Search">
            </form>
            <hr>
        </body>
    </html>
    """

@app.get("/run")
def run_agent(prompt: str):
    if "tesco" in prompt.lower() or "beer" in prompt.lower():
        try:
            deals = scrape_tesco_beer_deals()
            return JSONResponse(content={"results": deals})
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)
    return {"response": "Prompt not recognized. Try including 'beer' or 'Tesco'."}
