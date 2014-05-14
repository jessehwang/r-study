import sublime, sublime_plugin
import os, codecs
import urllib
from html.parser import HTMLParser


VERSION = "0.01"
WEB_DIC_URL = "http://endic.naver.com/search.nhn?%s"

WEB_DIC_OPTIONS = {'query' : 'test',
          			'searchOption' : 'thesaurus',}

TARGET_BLOCK_TAG = 'span'
TARGET_KEYWORD = '[유의어]' 
TARGET_SYNONYM_TAG = 'a'

# Python idiom: os-independent file path 

package_path = os.path.join(sublime.packages_path(), "cwkWritingToolKit")
WORD_FILE_PATH = os.path.join("Dictionaries", "dictionary.cwktxt")
WORD_FILE_PATH  = os.path.join(package_path, WORD_FILE_PATH)


class WebDicParser(HTMLParser):
	def __init__(self):
		super().__init__(self)
		self._is_in_block = False
		self._target_block_tag_found = False
		self._target_synonym_tag_found = False
		self._target_defs_tag_found = False
		self._is_final_tag = False

	def handle_starttag(self, tag, attrs):
		if tag == TARGET_BLOCK_TAG:
			if self._is_in_block and self._is_final_tag:
				self.reset_tags()
				self._target_defs_tag_found = True
			else:
				self._target_block_tag_found = True


		elif tag == TARGET_SYNONYM_TAG and self._is_in_block:
			# synonym tag found
			self._target_synonym_tag_found = True
		else:
			self.reset_tags()

	def handle_endtag(self, tag):
		pass
		
	def handle_data(self, data):
		if not self._is_in_block and self._target_block_tag_found and data.strip() == TARGET_KEYWORD:
			self._is_in_block = True
			print("Keyword:", data)
		elif self._is_in_block and self._target_synonym_tag_found:
			print ("Synonym:" , data)
			self._target_synonym_tag_found = False
			self._is_final_tag = True
		elif self._target_defs_tag_found:
			print ("Defs:", data)
			self.reset_tags()
		else:
			self.reset_tags()


	def reset_tags(self):
		self._is_in_block = False
		self._target_block_tag_found = False
		self._target_synonym_tag_found = False
		self._target_defs_tag_found = False
		self._is_final_tag = False

class CwkFetchWebDic(sublime_plugin.TextCommand):
	def run(self, edit):
		options = urllib.parse.urlencode(WEB_DIC_OPTIONS)
		request = urllib.request.Request(WEB_DIC_URL % options)
		response = urllib.request.urlopen(request)
		webpage = response.read().decode('utf-8')

		parser = WebDicParser()
		parser.feed(webpage)

# cwk_insert_selected_text command inserts text at cursor position
# camel casing: CwkInsertSelectedText
# snake casing: cwk_insert_selected_text
# Sublime Text translates camel cased commands into snake cased ones.
# You can run snake cased command by calling the view's run_command() method as the following:
# 	view.run_command("cwk_insert_selected_text", text_to_insert)

class CwkInsertSelectedText(sublime_plugin.TextCommand):
	def run(self, edit, args):
		
		# get current cursor position
		# Sublime Text supports multiple cursors: view.sel() returns the list of those cursors. The first element of the list refers to the current cursor position.
		# view.word() returns the region of the current word.

		cursor = self.view.sel()[0]
		word_region = self.view.word(cursor)
		word = self.view.substr(word_region) 

		# view.replace() replaces the selected word with the given text. edit is the buffer currently in use.

		self.view.replace(edit, word_region, args['text'])
 
class CwkAutoComplete(sublime_plugin.WindowCommand):
	def __init__(self, window):

		# super() refers to the immediate ancestor: sublime_plugin.WindowCommand in this case.

		super().__init__(window)

		# Sublime Text idiom: read settings

		self.plugin_settings = sublime.load_settings("cwkWritingToolKit.sublime-settings")
		self.debug = self.plugin_settings.get("debug", False)

		# get active window and view

		window = sublime.active_window()
		view = window.active_view()

		# save the word at the cursor position

		self.currentWord = view.substr(view.word(view.sel()[0].begin()))

		# self._words stores all found words whereas self._normalizedWords stores unique values.

		self._words = self.getWords(WORD_FILE_PATH)
		self._normalizedWords = []
		
	def run(self): 
	# run method is triggered when this cwk_auto_comoplete command is called

		window = sublime.active_window()
		view = window.active_view()

		# self.log() spits out messages only when debug mode is on, that is, set to true.

		self.log("view id: ", view.view_id)
		self.currentWord = view.substr(view.word(view.sel()[0].begin()))
		self.log("current word:", self.currentWord)
		self.normalizeWords()

		# view.shop_popup_menu() displays a popout menu presenting the words that contain the self.currentWord.
		# self.on_done is a callback method to be called when a selection is made.

		view.show_popup_menu(self._normalizedWords, self.on_done)

	def on_done(self, index):
	#show_popup_menu callback method 
	
		# if the use canceled out of the popout menu, -1 is returned. Otherwise the index is returned.

		if index == -1: return

		selected_string = self._normalizedWords[index]
		self.log("Word selected: " , selected_string)
		window = sublime.active_window()
		view = window.active_view()

		# run Text Command cwk_insert_selected_text to replace the current word with the user's choice

		view.run_command("cwk_insert_selected_text", {"args": {'text': selected_string.strip()} })

	def getWords(self, filename):
	# creates a autocomplete dictionary from the dictionary file

		word_lines = []
		if os.path.isfile(filename): 

			# normal file operations won't work with Korean characters. use codecs library instead.  
			# open() method returns a file handle and readlines() method returns the file contents as a list of lines.

			f = codecs.open(filename, "r", "utf-8")
			word_lines = f.readlines()
			self.log("cwk Dictionary Num Words Found: ", len(word_lines))
		else:
			self.log("cwk Dictionary file not found: ", filename)
		return word_lines

	def normalizeWords(self):
	# selects only those words that match the current word

		# Python idiom: list comprehension
		# discards the words not matching the current word and strip whitespaces at both ends

		self._normalizedWords = [ w.strip() for w in self._words if self.currentWord in w ]
		
	def log(self, *message):
	# utility method to print out debug messages

		# note that print is not a statement anymore in Python 3. It's a function.
		# print "blah blah" will give you an error
		# use print("blah blah") instead

		if(self.debug):
			print (*message)

