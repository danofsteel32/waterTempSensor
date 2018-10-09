import flask
import json
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as md
import scipy.interpolate as inter
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://joker:WPQ!!&(^@localhost/chicken_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Sensor(db.Model):
	__tablename__ = 'sensors_data'
	__table_args__ = tuple(db.UniqueConstraint('record_time', 'device_id', 'data_type', 'data_value'))

	record_time = db.Column(db.DateTime, nullable=False, primary_key=True)
	device_id = db.Column(db.String(120), nullable=False)
	data_type = db.Column(db.String(120), nullable=False)
	data_value = db.Column(db.Integer, nullable=False)

	def __repr__(self):
		return "<Sensor(record_time='%s', device_id='%s', data_type='%s', data_value='%s')>" % (
			self.record_time, self. device_id, self.data_type, self.data_value)

def retrieve_most_recent():
	try:
		sensor = Sensor.query.order_by(db.text('record_time desc')).limit(1).one()
		sensor_dict = {
			'time': sensor.record_time.strftime('%c'),
			'device': sensor.device_id,
			'data_type': sensor.data_type,
			'data_value': sensor.data_value
		}
		return sensor_dict
	except Exception as e:
		print('Nothing in the DB')
		return {}

def retrieve_interval(device_id, hours):
	data_interval = datetime.now() - timedelta(hours = hours)

	try:
		sensor = Sensor.query.filter(Sensor.device_id == device_id, Sensor.record_time > data_interval).order_by(db.text('record_time desc')).all()
		return sensor
	except Exception as e:
		print(e)

def create_chart(device_id, interval):
	xfmt = md.DateFormatter('%H:%M:%S')
	tick_stride = 1
	step = -1.0
	exp = 1.0

	if interval == 'hour':
		hours = 1
		tick_stride = 6
		retrieve_interval(device_id, hours)
	elif interval == 'day':
		hours = 24
		tick_stride = 8
		exp = 1.5
		retrieve_interval(device_id, hours)
	elif interval == 'week':
		hours = 168
		tick_stride = 7
		exp = 2.25
		xfmt = md.DateFormatter('%a %H:%M:%S')
		retrieve_interval(device_id, hours)

	time_list = []
	data_list = []
	data_type = ''

	for row in retrieve_interval(device_id, hours):
		time_list.append(row.record_time)
		data_list.append(row.data_value)
		data_type = row.data_type

	tick_list = []

	for i in range(0, len(time_list), max(1, int(len(time_list) / tick_stride))):
		tick_list.append(time_list[i])

	x_list = np.array([md.date2num(t) for t in time_list])
	y_list = np.array(data_list)

	x_new = x_list
	y_new = y_list

	if step > 0:
		step *= (y_list.max() - y_list.min()) ** exp
		sp = inter.UnivariateSpline(x_list, y_list, s=step)
		x_new = np.linspace(x_list.min(), x_list.max(), 1000)
		y_new = sp(x_new)

	plt.title('Last %s' % interval)
	plt.xlabel('Time', fontsize=14)
	plt.ylabel(data_type, ha='left', fontsize=14)
	plt.xticks(md.date2num(tick_list))
	plt.xticks(rotation=30)
	plt.gcf().subplots_adjust(bottom=0.25, left=0.15)

	ax = plt.gca()
	ax.xaxis.set_label_coords(0.48, -0.28)
	ax.yaxis.set_label_coords(-0.1, 0.3)
	ax.xaxis.set_major_formatter(xfmt)
	ax.plot(x_new, y_new, 'b')
	ax.grid(True)
	ax.margins(0.025) 

	img = BytesIO()
	plt.savefig(img)
	plt.clf()
	img.seek(0)
	#plt.show()
	return flask.send_file(img, mimetype='image/png')

@app.route('/', methods=['GET'])
def front_page():
	return flask.render_template('dash.html')

@app.route('/charts/<device_id>/<interval>')
def serve_chart(device_id, interval):
	return create_chart(device_id, interval)

@app.route('/query', methods=['POST'])
def query(): 
	return json.dumps(retrieve_most_recent())

@app.route('/update', methods=['POST'])
def update_data():
	data = {}
	try:
		data = request.get_json()
	except Exception as e:
		print(e)
	print(data)
	try:
		insert_row = Sensor(record_time=datetime.now().replace(microsecond=0), device_id=data['device_id'], data_type=data['data_type'], data_value=data['data_value'])
		db.session.add(insert_row)
		db.session.commit()
	except Exception as e:
		print(e)
	return json.dumps(data)

if __name__ == '__main__':
	db.create_all() # for testing only
	#print(retrieve_most_recent())
	#retrieve_interval('water_temp1', 'hour')
	#create_chart('water_temp1', 'hour')
	app.run(host='0.0.0.0', port=8000, debug=True)