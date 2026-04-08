import os
from app import create_app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    if debug:
        app.run(debug=True, host="127.0.0.1", port=port)
    else:
        from waitress import serve
        serve(app, host="0.0.0.0", port=port)
        
        #cloudflared tunnel --url http://localhost:5001