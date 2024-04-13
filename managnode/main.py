# Copyright 2023 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Manager node."""

from quart import Quart, request

app = Quart(__name__)


@app.route("/v1/report/", methods=["POST"])
async def report():
    content = await request.get_data()
    print("======= report from distnode", content)
    return "OK"


@app.route("/v1/status/", methods=["POST"])
async def status():
    content = await request.get_data()
    print("======= status from distnode", content)
    return "OK"

@app.route("/v1/crash/", methods=["POST"])
async def crash():
    content = await request.get_data()
    print("======= CRASH from distnode", content)
    return "OK"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
