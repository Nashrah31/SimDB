# app.py
from flask import Flask  # import flask
from flask import request  # import flask

from flask import jsonify
from vectorizers.img_to_vec import Img2Vec
from util.ImageUtils import ImageUtils
import time
import atexit
from settings.config import Config
from factory import Factory

from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)  # create an app instance
img2vec = Img2Vec()

port = 8082
host = '0.0.0.0'
debug = True

config = Config()
components_factory = Factory(config)

indexer = components_factory.get_indexer()
content_vectors = components_factory.get_content_vector_store()
result_mapper = components_factory.get_result_mapper()
writer = components_factory.get_writer()
image_utils = ImageUtils(img2vec)


@app.route("/api/v1/train", methods=['POST'])  # at the end point /
def training():  # call method training
  # content_vectors.load_csv('./assets/livemint-cv2.csv')
  # content_vectors.load_json('./assets/july2020.json')
  indexer.build_index(content_vectors)
  return "created indexes successfully"


@app.route("/api/v1/query", methods=['POST'])  # at the end point /
def query():  # call method training
  rq = request.json
  default_nn = config.default_nn()
  result = indexer.find_NN_by_id(rq.get("id"), default_nn)
  is_string = (type(rq.get("id")) is str)
  response = jsonify(result_mapper.map(result, is_string))
  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


@app.route("/api/v1/content", methods=['POST'])  # at the end point /
def vectorize_and_add():
  content_list = request.json
  content_vector_list = image_utils.vectorize_images(content_list)
  content_vectors.add_content_vectors(content_vector_list)
  indexer.build_index(content_vectors)
  return "created indexes successfully"


@app.route("/api/v1/content-vectors", methods=['POST'])  # at the end point /
def add_vectors():
  content_list = request.json
  content_vectors.add_content_vectors(content_list)
  return "created indexes successfully"


def print_date_time():
  print(time.strftime("%A, %d. %B %Y %I:%M:%S %p"))


def reindex_and_export():
  indexer.build_index()
  ids = content_vectors.get_all_ids()
  writer.write(ids, indexer)


scheduler = BackgroundScheduler()
scheduler.add_job(name="reindex_and_export", func=reindex_and_export, trigger="interval", seconds=29)

if not config.is_streaming_reader():
  content_vectors.read()
else:
  scheduler.add_job(name="content_read", func=content_vectors.read, trigger="interval", seconds=19)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":  # on running python app.py
  app.run(host=host, port=port, debug=debug, use_reloader=False)
