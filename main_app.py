from sanic import Sanic
from sanic.response import text

app = Sanic("Web Server")

@app.route('/')
async def test(request):
    return text("Test")

if __name__ == '__main__':
    app.run()