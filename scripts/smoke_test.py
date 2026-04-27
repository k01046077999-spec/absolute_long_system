from strategy.scanner import scan

if __name__ == "__main__":
    result = scan(mode="sub", limit=30)
    print(result["strategy"], result["mode"], result["count"])
    for item in result["candidates"][:3]:
        print(item["ticker"], item["name"], item["type"], item["score"])
