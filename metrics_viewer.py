from tkinter import *
import sys
import os
import json
from pprint import pprint

from config import config

from advanced_zoom import Zoom_Advanced

import heatmap as hm

import PIL


class MetricsViewer:

	root = Tk()

	useTime = IntVar(value=0) #should we use the viewTime variable
	viewTime = IntVar() # game time around which to show data

	mapOptions = ["damage recieved",
							"movement"]
	mapType = StringVar(value = mapOptions[0])
	
	# max seconds to show in the timeline
	maxTime = 1
	
	timelinePrecision = 100 #timeline slider increments

	
	def main(self):

		self.root.title("Sky Command Metrics Viewer")
		self.root.geometry("800x600")
		
		#buttons
		self.reload = Button(self.root, text='Reload', command=self.readMetrics)
		self.reload.grid(row=0, column=0, columnspan=1, rowspan=1, padx=5, pady=5)

		self.map_optionmenu = OptionMenu(self.root, self.mapType, *self.mapOptions, command=self.changeMap)
		self.map_optionmenu.grid(row = 0, column = 1, columnspan=1, rowspan=1, padx=5, pady=5)
		
		#info
		self.info_frame = Frame(self.root, bd = 5)
		self.info_frame.grid(row=1, column=3, columnspan=1, rowspan=2, padx=5, pady=5, sticky=N+S+W+E)
		
		self.zones_label = Label(self.info_frame, text = "test label", anchor=W, justify=LEFT)
		self.zones_label.grid(row = 0, column = 0, sticky=W)
		
		self.dmg_label = Label(self.info_frame, text = "test label", anchor=W, justify=LEFT)
		self.dmg_label.grid(row = 1, column = 0, sticky=W)
		
		#map		
		self.map_frame = Frame(self.root)
		self.map_frame.grid(row=1, column=0, columnspan=3, rowspan=1, padx=0, pady=0 , sticky=N+S+W+E)

		# --------------------------
		# load data 
		self.readMetrics()
		
		# create heatmap
		self.setup_config(self.damage_map_generator())
		self.map_iter = self.damage_map_generator
		self.generate_heatmap()
		# --------------------------
		
		self.map = Zoom_Advanced(self.map_frame, image=self.heatmap_image)
		self.map.grid(row = 0, column = 0, sticky=N+E+S+W)
		#map_img = PhotoImage(file=config["map_img"])
		
		#self.map_label = Label(self.map_frame, image=map_img, width = 600, height = 600)
		#self.map_label.pack(side = LEFT, fill = BOTH, expand = True)
		
		# timeline
		self.check = Checkbutton(self.root, text='', 
			command=self.useTimeChanged, variable=self.useTime)
		self.check.grid(row=2, column=0, columnspan=1, rowspan=1, padx=5, pady=5)
		
		self.timeline = Scale(self.root, from_=0, to=self.timelinePrecision, orient=HORIZONTAL, showvalue=False,
			command=self.viewTimeChanged, variable=self.viewTime)
		self.timeline.grid(row=2, column=2, columnspan=1, rowspan=1, padx=5, pady=5, sticky=E+W)

		self.timelineLabel = Label(self.root, text = "0")
		self.timelineLabel.grid(row=2, column=1, columnspan=1, rowspan=1, padx=5, pady=5)

		# layout
		self.root.grid_rowconfigure(0, minsize=5, pad=0, weight=1)
		self.root.grid_rowconfigure(1, minsize=50, pad=0, weight=10)
		self.root.grid_rowconfigure(2, minsize=5, pad=0, weight=1)
		
		self.root.grid_columnconfigure(0, minsize=10, pad=0, weight=1)
		self.root.grid_columnconfigure(1, minsize=10, pad=0, weight=1)
		self.root.grid_columnconfigure(2, minsize=100, pad=0, weight=10)
		self.root.grid_columnconfigure(3, minsize=50, pad=0, weight=5)
		
		self.root.mainloop()
		
	def changeMap(self, var):
		print("Change Map to " + str(var))
		func = None
		if var == "damage recieved":
			print("name recognized as Damage Recieved")
			func = self.damage_map_generator
		elif var == "movement":
			print("name recognized as Player Movement")
			func = self.movement_map_generator
		if func is not None:
			self.map_iter = func
			self.generate_heatmap()
			self.map.change_image(self.heatmap_image)
		
	def useTimeChanged(self):
		#print("UseTime checkbox changed to " + str(self.useTime.get()))
		if self.useTime.get() == 0:
			self.timeline.configure(state="disabled")
		else:
			self.timeline.configure(state="normal")
		
		self.generate_heatmap()
		self.map.change_image(self.heatmap_image)
		
	def getCurrentViewTime(self):
		return self.maxTime * self.viewTime.get() / self.timelinePrecision
		
	def viewTimeChanged(self, pos):
		#print("ViewTime slider changed to " + str(self.viewTime.get()))
		self.timelineLabel.configure(text = "{:6.1f}".format(self.getCurrentViewTime()))
		
		self.generate_heatmap()
		self.map.change_image(self.heatmap_image)
		
	def readMetrics(self):
		self.maxTime = 0
		
		data = {}
		data["zones"] = []
		data["player_dmg"] = []
		data["player_move"] = []
		
		print("Found metrics files:")
		for root, dirs, files in os.walk(config["load_dir"]):
			for file in files:
				print(file)
				
				file_data = json.load(open(root + file))
				
				#pprint(file_data)
				
				if "zones" in file_data:
					data["zones"] += file_data["zones"]
					
				if "playerDamageEvents" in file_data:
					data["player_dmg"].append( [] + file_data["playerDamageEvents"] )
					
				if "playerPositions" in file_data:
					data["player_move"] += file_data["playerPositions"]
		
		self.data = data
		
		# ZONES
		zone_avgs = {}
		for zone in data["zones"]:
			zoneName = zone["zoneName"]
			if zone["timeStop"] < zone["timeStart"]: continue
			if zoneName not in zone_avgs:
				zone_avgs[zoneName] = {"count":0, "avg": 0}
			avg = zone_avgs[zoneName]["avg"]
			avg = ( zone_avgs[zoneName]["count"] * avg + (zone["timeStop"] - zone["timeStart"]) ) / (zone_avgs[zoneName]["count"] + 1)
			zone_avgs[zoneName]["avg"] = avg
			zone_avgs[zoneName]["count"] += 1
			
			if(zone["timeStop"] > self.maxTime):
				self.maxTime = zone["timeStop"]
		
		zone_text = "Average Times:\n"
		for zone in zone_avgs.keys():
			zone_text += zone + ": " + "{:6.1f}".format(zone_avgs[zone]["avg"]) + "\n"
		
		self.zones_label.configure(text = zone_text)
		
		#PLAYER DAMAGE
		
		#TODO: make sure unrepresented enemy types get totaled as 0 for averages
		self.damage_events = []
		avg_damage = {}
		for dmgs in data["player_dmg"]:
			damage_totals = {}
			for dmg in dmgs:
				enemyType = dmg["enemyType"] 
				
				if enemyType != "NonEnemy":
					self.damage_events.append({"amount": dmg["damageAmount"], "position": dmg["playerLocation"], "time": dmg["time"]})
				
				if enemyType not in damage_totals:
					damage_totals[enemyType] = {"total":0}
				damage_totals[enemyType]["total"] += dmg["damageAmount"]
				
				if(dmg["time"] > self.maxTime):
					self.maxTime = dmg["time"]
					
			for enemy in damage_totals.keys():
				if enemy not in avg_damage:
					avg_damage[enemy] = {"count":0, "avg": 0}
				avg = avg_damage[enemy]["avg"]
				avg = ( avg_damage[enemy]["count"] * avg + (damage_totals[enemy]["total"]) ) / (avg_damage[enemy]["count"] + 1)
				avg_damage[enemy]["avg"] = avg
				avg_damage[enemy]["count"] += 1
		
		dmg_text = "Average Total Damage:\n"
		for enemy in avg_damage.keys():
			dmg_text += enemy + ": " + "{:4.0f}".format(avg_damage[enemy]["avg"]) + "\n"
		
		self.dmg_label.configure(text = dmg_text)
		
		#PLAYER MOVEMENT
		self.player_movement = []
		
		for move in data["player_move"]:
			self.player_movement.append({"position": move["playerLocation"], "time": move["time"]})
	
		pass
	
	def vector3_to_latlon(self, data):
		pt = ((data["z"] - config["map_bounds"]["min"]["z"]) / (config["map_bounds"]["max"]["z"] - config["map_bounds"]["min"]["z"]) * self.map_size[0],
				(data["x"] - config["map_bounds"]["min"]["x"]) / (config["map_bounds"]["max"]["x"] - config["map_bounds"]["min"]["x"]) * self.map_size[1])
		
		#print("point on image: " + str(pt))
		
		latlon = self.hm_config.projection.inverse_project(hm.Coordinate(*pt))
		
		return latlon
		
	def damage_map_generator(self):
		for event in self.damage_events:
			if self.useTime.get() == 1 and abs(self.getCurrentViewTime() - event["time"]) > 10: continue
			latlon = self.vector3_to_latlon(event["position"])
			yield hm.Point(latlon,weight=event["amount"])
	
	def movement_map_generator(self):
		for event in self.player_movement:
			if self.useTime.get() == 1 and abs(self.getCurrentViewTime() - event["time"]) > 10: continue
			latlon = self.vector3_to_latlon(event["position"])
			yield hm.Point(latlon,)
	
	def generate_heatmap(self):
		self.hm_config.shapes = self.map_iter()
		if len([s for s in self.map_iter()]) == 0: 
			self.heatmap_image = PIL.Image.open(config["map_img"])
			return
		matrix = hm.process_shapes(self.hm_config)
		matrix = matrix.finalized()
		self.heatmap_image = hm.ImageMaker(self.hm_config).make_image(matrix)
			
	def setup_config(self, iter):
		map = PIL.Image.open(config["map_img"])
	
		self.map_size = map.size
		
		self.hm_config = hm.Configuration()
		self.hm_config.width = map.size[0]
		self.hm_config.height = map.size[1]
		self.hm_config.margin = 0
		self.hm_config.zoom = 1
		self.hm_config.projection = hm.EquirectangularProjection()
		self.hm_config.projection.pixels_per_degree = 1
		self.hm_config.extent_out = hm.Extent(coords = [hm.Coordinate(c[0],c[1]) for c in [(0,0),map.size]])
		self.hm_config.extent_in = hm.Extent(coords = [self.hm_config.projection.inverse_project(hm.Coordinate(c[0],c[1])) for c in [(0,0),map.size]])
		self.hm_config.shapes = iter
		self.hm_config.decay = 0.5
		self.hm_config.kernel = hm.LinearKernel(5)
		self.hm_config.background_image = map
		self.hm_config.fill_missing()
		return config
		
if __name__ == "__main__":
	print(sys.version)
	
	
	
	viewer = MetricsViewer()
	viewer.main()
	print("Program ran.")