from flask import Flask, jsonify

product = [{'name':'Grape','price' : 10}]
def create_app():
    app = Flask(__name__)

    return app

app = create_app()


@app.route("/products")
def products(): 
    return jsonify(product),200

if (__name__== "__main__"):
    app.run(debug=True)
