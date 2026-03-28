import sys

if "--serve" in sys.argv:
    import uvicorn
    port = 8000
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    uvicorn.run("src.api:app", host="0.0.0.0", port=port, log_level="info")
else:
    from src.runner import run
    run()
