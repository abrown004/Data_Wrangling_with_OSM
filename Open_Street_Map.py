'''
P3 Data Wrrangling - Open Street Map Case Study
''' 



'''
Call out Python packages and variables
'''
import csv
import xml.etree.cElementTree as ET
import pprint
import re
import codecs
from collections import defaultdict

osm_file = "Oakland.osm"

NODE_FIELDS = ['id', 'lat', 'lon', 'version', 'timestamp', 'changeset', 'uid',  'user']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"


'''
Parse the OSM Datafile to View and County the XML Tags
'''
def count_tags(filename):
	tags = {}
	for event, elem in ET.iterparse(filename):
		if elem.tag not in tags:
			tags[elem.tag] = 1
		else:
			tags[elem.tag] += 1
	return tags

tags = count_tags(osm_file)
pprint.pprint(tags)


'''
Helper Functions for Data Fixing
'''
# for uid  and id values
def fix_int(expected_int):
	try:
		if int(expected_int):
			expected_int = int(expected_int)
	except ValueError:
		expected_int = None

	return expected_int

# for lat and lon values
def fix_float(expected_float):
	try:
		if float(expected_float):
			expected_float = float(expected_float)
	except ValueError:
		expected_float = None

	return expected_float


'''
Fixing Street Names
'''
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)


expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
			"Trail", "Parkway", "Commons"]

# List of Abbreviations
mapping = { "St": "Street",
			"Ave": "Avenue",
			"Blvd": "Boulevard",
			"Dr": "Drive",
			"Ct": "Court",
			"Pl": "Place",
			"Sq": "Square",
			"Ln": "Lane",
			"Rd": "Road",
			"Tr": "Trail",
			"Pkwy": "Parkway",
			"Cmns": "Commons"           
			}

def audit_street_type(street_types, street_name):
	m = street_type_re.search(street_name)
	if m:
		street_type = m.group()
		if street_type not in expected:
			street_types[street_type].add(street_name)

def is_street_name(elem):
	return (elem.attrib['k'] == "addr:street")

def audit(osmfile):
	osm_file = open(osmfile, "r")
	street_types = defaultdict(set)
	for event, elem in ET.iterparse(osm_file, events=("start",)):

		if elem.tag == "node" or elem.tag == "way":
			for tag in elem.iter("tag"):
				if is_street_name(tag):
					audit_street_type(street_types, tag.attrib['v'])
	osm_file.close()
	return street_types

audit(osm_file)

def update_name(name, mapping):
	for item in mapping:
		if item in name:
			name = name.replace(".","")
			name = name.replace(item,mapping[item],1)
	return name

'''
Helper Functions for Filetype Conversion
'''
# Extract xml element from file
def get_element(osm_file, tags=('node')):
	"""Yield element if it is the right type of tag"""

	context = ET.iterparse(osm_file, events=('start', 'end'))
	_, root = next(context)
	for event, elem in context:
		if event == 'end' and elem.tag in tags:
			yield elem
			root.clear()

def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS, problem_chars=PROBLEMCHARS, default_tag_type='regular'):
	"""Clean and shape node XML element to Python dict"""

	node_attribs = {}
	way_attribs = {}
	way_nodes = []
	tags = []  # Handle secondary tags the same way for both node and way elements
	
	# Sort the Node elements
	if element.tag == 'node':
		for field in node_attr_fields:
			if field in element.attrib:
				# Audit integer fields
				if field == "id" or field == "uid":
					node_attribs[field] = fix_int(element.attrib[field])
				# Audit lat/lon fields
				elif field == "lat" or field == "lon":
					node_attribs[field] = fix_float(element.attrib[field])
				else:
					node_attribs[field] = element.attrib[field]
			else:
				node_attribs[field] = None
		for child in element:
			# check for problem characters
			if problem_chars.search(child.attrib["k"]) == None:
				node_tags = {}
				# add value for "id" if value is an integer
				node_tags["id"] = fix_int(element.attrib["id"])
				node_tags["value"] = child.attrib["v"]
				if ":" in child.attrib["k"]:
					data_type = child.attrib["k"].split(":",1)[0]
					#test if attribute is a street name
					if is_street_name(child):
						value = update_name(child.attrib["k"].split(":",1)[1], mapping)
					else:
						value = child.attrib["k"].split(":",1)[1]
					node_tags["key"] = value
					node_tags["type"] = data_type
				else:
					node_tags["key"] = child.attrib["k"]
					node_tags["type"] = default_tag_type
				tags.append(node_tags)
		return {'node': node_attribs, 'node_tags': tags}
	
	# Sort the Way Elements
	elif element.tag == 'way':
		count = 0
		for field in way_attr_fields:
			if field in way_attr_fields:
				# Audit integer fields
				if field == "id" or field == "uid":
					way_attribs[field] = fix_int(element.attrib[field])
				else:
					way_attribs[field] = element.attrib[field]
			else:
				way_attribs[field] = None
		for child in element:
			if child.tag == "nd":
				way_nd = {}
				# add value for "id" if value is an integer
				way_nd["id"] = fix_int(element.attrib["id"])
				way_nd["node_id"] = fix_int(child.attrib["ref"])
				way_nd["position"] = count
				way_nodes.append(way_nd)
				count += 1
			elif child.tag == "tag":
				if problem_chars.search(child.attrib["k"]) == None:
					way_tags = {}
					# add value for "id" if value is an integer
					way_tags["id"] = fix_int(element.attrib["id"])
					way_tags["value"] = child.attrib["v"]
					if ":" in child.attrib["k"]:
						#test if attribute is a street address
						if is_street_name(child):
							data_type = "addr"
							value = update_name(child.attrib["k"].split(":",1)[1], mapping)
						else:
							data_type = child.attrib["k"].split(":",1)[0]
							value = child.attrib["k"].split(":",1)[1]
						way_tags["key"] = value
						way_tags["type"] = data_type
					else:
						way_tags["key"] = child.attrib["k"]
						way_tags["type"] = default_tag_type
					tags.append(way_tags)
		return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}

class UnicodeDictWriter(csv.DictWriter, object):
	"""Extend csv.DictWriter to handle Unicode input"""

	def writerow(self, row):
		super(UnicodeDictWriter, self).writerow({
			k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
		})

	def writerows(self, rows):
		for row in rows:
			self.writerow(row)

'''
Extract Data to Python Dictionary and Write to CSV Files
'''
with codecs.open(NODES_PATH, 'w') as nodes_file, \
	codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
	codecs.open(WAYS_PATH, 'w') as ways_file, \
	codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
	codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:
		
	nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
	node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
	ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
	way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
	way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)
	
	nodes_writer.writeheader()
	node_tags_writer.writeheader()
	ways_writer.writeheader()
	way_nodes_writer.writeheader()
	way_tags_writer.writeheader()
	
	#validator = cerberus.Validator()

	for element in get_element(osm_file, tags=('node', 'way')):
		el = shape_element(element)
		
		if el:
			#if validate is True:
				#validate_element(el, validator)

			if element.tag == 'node':
				nodes_writer.writerow(el['node'])
				node_tags_writer.writerows(el['node_tags'])
			elif element.tag == 'way':
				ways_writer.writerow(el['way'])
				way_nodes_writer.writerows(el['way_nodes'])
				way_tags_writer.writerows(el['way_tags'])