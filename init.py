from app import init_app

app = init_app()

if __name__ == '__main__':
    print("runnning app")
    app.run(port=8080, debug=True)
