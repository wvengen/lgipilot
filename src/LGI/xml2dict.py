#
# Copyright (C) 2011 W. van Engen, Stichting FOM, The Netherlands
# Copyright (C) 2010 M.F. Somers, Theoretical Chemistry Group, Leiden University
#
# This is free software; you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation.
#
# http://www.gnu.org/licenses/gpl.txt

import binascii

class __NotATextNode( Exception ):
	pass

def xml2dict( Node ):
	'''Convert dom to nested dict.

	Attributes are converted to elements. If multiple nodes of the same
	name are present, it will become a list of nodes.

	The contents of nodes named 'input' or 'output' is un-hexbin-ed

	@type Node xml.dom.minidom
	@param Node DOM to convert
	@rtype dict
	@return nested dict with the contents of the DOM as dict or str
	'''
	Counts = {}
	Dict = {}

	for n in Node.childNodes:
		if n.nodeType != n.ELEMENT_NODE:
			continue

		NodeName = n.nodeName

		if NodeName in Counts.keys():
			Counts[ NodeName ] = Counts[ NodeName ] + 1;	
			Dict[ NodeName ] = []
		else:
			Counts[ NodeName ] = 1
	if Node.attributes:
		for a in Node.attributes.keys():
			if a in Counts.keys():
				Counts[ a ] = Counts[ a ] + 1
				Dict [ a ] = [ Node.attributes[a].value ]
			else:
				Counts[ a ] = 1
				Dict [ a ] = Node.attributes[a].value
	
	for n in Node.childNodes:
		if n.nodeType != n.ELEMENT_NODE:
			continue

		NodeName = n.nodeName

		try:
			Text = ""

			for nn in n.childNodes:
				if nn.nodeType == nn.TEXT_NODE:
					Text = Text + nn.nodeValue
				else:
					raise __NotATextNode

			Text = Text.strip( "\n\r\t " )

		except __NotATextNode:

			SubDict = xml2dict( n )

			if Counts[ NodeName ] > 1:
				Dict[ NodeName ].append( SubDict )
			else: 
				Dict[ NodeName ] = SubDict

			continue

		if NodeName == "input" or NodeName == "output":
			Text = binascii.a2b_hex( Text )
		else:
			if Text.isdigit():
				Text = int( Text )
			else:
				Text = Text

		if Counts[ NodeName ] > 1:
			Dict[ NodeName ].append( Text )
		else:
			Dict[ NodeName ] = Text

	return Dict

