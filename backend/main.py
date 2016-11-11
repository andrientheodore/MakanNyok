import json
import tensorflow as tf
import os
from datetime import timedelta
from functools import update_wrapper
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from flask import Flask,jsonify,request,make_response, request, current_app


app = Flask(__name__)

# Global Limits for API Request is 100 Request per second
limiter = Limiter(
	app,
	key_func=get_remote_address,
	global_limits=["100 per second"],
)

# Allowed Extensions 
# Currently only support JPG & JPEG
ALLOWED_EXTENSIONS = set(['jpg', 'jpeg'])

# Maximum Content Size ( 2MB )
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

# Function to check file types
def allowed_file(filename):
	return '.' in filename and \
		   filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# Function to manage Cross Domain Origins
def crossdomain(origin=None, methods=None, headers=None,
				max_age=21600, attach_to_all=True,
				automatic_options=True):
	if methods is not None:
		methods = ', '.join(sorted(x.upper() for x in methods))
	if headers is not None and not isinstance(headers, basestring):
		headers = ', '.join(x.upper() for x in headers)
	if not isinstance(origin, basestring):
		origin = ', '.join(origin)
	if isinstance(max_age, timedelta):
		max_age = max_age.total_seconds()

	def get_methods():
		if methods is not None:
			return methods

		options_resp = current_app.make_default_options_response()
		return options_resp.headers['allow']

	def decorator(f):
		def wrapped_function(*args, **kwargs):
			if automatic_options and request.method == 'OPTIONS':
				resp = current_app.make_default_options_response()
			else:
				resp = make_response(f(*args, **kwargs))
			if not attach_to_all and request.method != 'OPTIONS':
				return resp

			h = resp.headers
			h['Access-Control-Allow-Origin'] = origin
			h['Access-Control-Allow-Methods'] = get_methods()
			h['Access-Control-Max-Age'] = str(max_age)
			h['Access-Control-Allow-Credentials'] = 'true'
			h['Access-Control-Allow-Headers'] = \
				"Origin, X-Requested-With, Content-Type, Accept, Authorization"
			if headers is not None:
				h['Access-Control-Allow-Headers'] = headers
			return resp

		f.provide_automatic_options = False
		return update_wrapper(wrapped_function, f)
	return decorator

# BoilerPlate code
@app.route("/")
def hello():
	return "It Works!"

# Handle 413 Entity is too large ( File size >2MB)
@app.errorhandler(413)
def fileIsTooLarge(error) :
	return jsonify(error="true", error_message="File is too large! Max is 2MB!")

# Main Route Function
@app.route("/predict/", methods=['POST'])
# Limit this /predict/ function for 90 Request / seconds
@limiter.limit("90 per second")
# For now Allow-All Request origins
# To-Do : Allow only specific domain
@crossdomain(origin='*')
def runPrediction():
	if request.method == "POST" and 'photo' in request.files:
		# Get Image from Request
		file = request.files['photo']

		# Check file extension
		if allowed_file(file.filename):
			file.save(os.path.join('tmp', secure_filename(file.filename)))
		else :
			return jsonify(error="true", error_message="Invalid Image Type");

		# Read in the image_data
		image_data = tf.gfile.FastGFile(('tmp/' + file.filename), 'rb').read()

		# Loads label file, strips off carriage return
		label_lines = [line.rstrip() for line 
						   in tf.gfile.GFile("retrained_labels.txt")]

		# Unpersists graph from file
		with tf.gfile.FastGFile("retrained_graph.pb", 'rb') as f:
			graph_def = tf.GraphDef()
			graph_def.ParseFromString(f.read())
			_ = tf.import_graph_def(graph_def, name='')

		# Begin Tensorflow 
		with tf.Session() as sess:
			# Feed the image_data as input to the graph and get first prediction
			softmax_tensor = sess.graph.get_tensor_by_name('final_result:0')
			
			predictions = sess.run(softmax_tensor, \
					 {'DecodeJpeg/contents:0': image_data})
			
			# Sort to show labels of first prediction in order of confidence
			top_k = predictions[0].argsort()[-len(predictions[0]):][::-1]
			
			MAX_SCORE = 0
			PredictedResult = ""
			for node_id in top_k:
				human_string = label_lines[node_id]
				score = predictions[0][node_id]
				# Check for Max Score
				if (score > MAX_SCORE) :
					MAX_SCORE = score
					PredictedResult = human_string

		# Open May_Contains json 
		with open('may_contains.json') as json_data:
		   may_contains = json.load(json_data)
		   # try to get PredictedResult ingridients
		   try :
			contains = may_contains.get(PredictedResult).get('may_contains')
		   except AttributeError :
			contains = ""

		return jsonify(error="false", prediction_result = PredictedResult, ingridients = contains)		
	else:
		return jsonify(error= "true", error_message = "Invalid Request Parameter")



if __name__ == "__main__":
	# Self-Signed Certificate
	# To-Do : Use LetsEncrypt certificate
	context = ('', '')
	app.run(host = '0.0.0.0', debug = True, ssl_context = context)
