from fastapi import FastAPI

app = FastAPI(title="Notification Service (Technical Test)")


@app.get("/")
def hello_world():
    return {"hello": "world"}
