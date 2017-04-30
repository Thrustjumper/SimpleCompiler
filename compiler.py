import re

class Patterns:
	VARIABLE_PATTERN = r"(?:[a-zA-Z][a-zA-Z0-9]*\.)*[a-zA-Z][a-zA-Z0-9]*"
	NUMBER_PATTERN = r"[0-9]+"
	STRING_PATTERN = r"[a-zA-Z0-9\?!'\"@#~*+/§$%&\(\)\-\\<>|]"
	IMPORT_STRING_PATTERN = r"[a-zA-Z][a-zA-Z_0-9]*"
	FUNCTION_STRING_PATTERN = r"[a-zA-Z][a-zA-Z_0-9]*"

class VariableTypes:
	NUMBER_VARIABLE = "NUMBER"
	STRING_VARIABLE = "STRING"
	OBJECT_VARIABLE = "OBJECT"

class GeneralInfo:
	DEFAULT_FILE_EXTENSION = "SIMPLE"
	ASM_FILE_EXTENSION = "ASM"

class SimpleCompiler:
	filePath = None # string containing file path
	fileName = None # stores the file name currently compiled
	sourceCodeLines = None # list of source code lines
	assemblerLines = [] # list of assembler instructions
	compilationErrors = [] # list which holds all the compilation erros occured
	knownLocalVariables = {} # dict which keeps track of all locally known variables
	knownGlobalVariables = {} # dict which keeps track of all globally known variables
	knownVariablesTypes = {} # holds all the types of the corresponding variables
	bpOffset = 4 # base pointer offset

	functionMode = False # determines whether instructions are part of a function
	functionPrecedingTabs = 0 # determines how many tabs are preceding the function instruction
	functionName = None # if function mode is enabled than this variable will hold the current functions name to which the instructions belong to

	statementPatterns = [re.compile(r"^[\t\s]*number\s+" + Patterns.VARIABLE_PATTERN + r"(?:\s+=\s+" + Patterns.NUMBER_PATTERN +r")?$"), 
						 re.compile(r"^[\t\s]*string\s+" + Patterns.VARIABLE_PATTERN + r"(?:\s+=\s+\".*" + Patterns.STRING_PATTERN + r".*\")?$"),
						 re.compile(r"^[\t\s]*" + Patterns.VARIABLE_PATTERN + r"\s+=\s+" + Patterns.NUMBER_PATTERN + r"$"),
						 re.compile(r"^[\t\s]*" + Patterns.VARIABLE_PATTERN + r"\s+=\s+" + Patterns.VARIABLE_PATTERN + r"$"),
						 re.compile(r"^[\t\s]*number\s+" + Patterns.VARIABLE_PATTERN + r"(?:\s+=\s+" + Patterns.VARIABLE_PATTERN +r")?$"),
						 re.compile(r"^[\t\s]*import\s+" + Patterns.IMPORT_STRING_PATTERN + r"$"),
						 re.compile(r"^[\t\s]*function\s+" + Patterns.FUNCTION_STRING_PATTERN + r"(?:\s+accepts\s+(?:string|number|object)\s+" + Patterns.VARIABLE_PATTERN + r"(?:\s*,\s*" + Patterns.VARIABLE_PATTERN + r")*)?\s*:$")]

	# index mapping to corresponding patterns
	NUMBER_VARIABLE_CREATION_AND_ASSIGNMENT = 0
	STRING_VARIABLE_CREATION_AND_ASSIGNMENT = 1
	NUMBER_VARIABLE_ASSIGNMENT = 2
	NUMBER_VARIABLE_VARIABLE_ASSIGNMENT = 3
	NUMBER_VARIABLE_CREATION_AND_VARIABLE_ASSIGNMENT = 4
	IMPORT_STATEMENT = 5
	FUNCTION_STATEMENT = 6	

	def __init__(self, filePath, assemblerLines = [], compilationErrors = [], knownLocalVariables = {}, knownGlobalVariables = {}, knownVariablesTypes = {}, bpOffset = 4):
		self.assemblerLines = assemblerLines
		self.compilationErrors = compilationErrors
		self.knownLocalVariables = knownLocalVariables
		self.knownGlobalVariables = knownGlobalVariables
		self.knownVariablesTypes = knownVariablesTypes
		self.bpOffset = bpOffset

		self.filePath = filePath
		self.fileName = filePath[filePath.rindex("\\") + 1:filePath.rindex(".")]
		self.__readFile()
		self.__compileFile()
		#self.__compileASMFile()


	def __readFile(self):
		file = open(self.filePath, "r")
		self.sourceCodeLines = file.read().split("\n") #.replace("\t", "")
		file.close()

	def logCompilationError(self, lineNumber, errorMsg):
		self.compilationErrors.append("line " + lineNumber.__str__() + " in " + self.fileName + "." + GeneralInfo.DEFAULT_FILE_EXTENSION +": " + errorMsg)

	# always returns the stack position of the variable as a hex value
	def retrieveStackPositionOfVariable(self, variableName):
		if variableName in self.knownLocalVariables:
			return "0" + hex(int(self.knownLocalVariables[variableName]))[2:] + "h"
		else:
			return "0" + hex(int(self.knownGlobalVariables[variableName]))[2:] + "h"


	def aquireFullyQualifiedVariableName(self, variableName):
		# if variable is already fully qualified no further operation is required
		if len(re.findall(r"\.", variableName)) == 0:
			return self.fileName + "." + variableName
		else:
			return variableName

	def createVariableAndAllocate(self, variableName):
		if not self.functionMode:
			self.knownGlobalVariables[variableName] = self.bpOffset
		else:
			self.knownLocalVariables[variableName] = self.bpOffset
		self.knownVariablesTypes[variableName] = VariableTypes.NUMBER_VARIABLE
		self.bpOffset += 4 # increment by four because integer(4 bytes) was added

	def __compileFile(self):
		lineCounter = 1
		for line in self.sourceCodeLines:
			for stmPattern in self.statementPatterns:
				instruction = re.findall(stmPattern, line)
				if len(instruction) > 0:
					instruction = instruction[0]

					if self.functionMode:
						precedingTabCount = len(re.findall(r"\t", instruction))
						if not precedingTabCount == self.functionPrecedingTabs + 1:
							self.assemblerLines.append("ret")
							self.assemblerLines.append(self.functionName + " endp")
							self.functionMode = False

					# ----------------------------------------------------------------------------------------------------------------------
					if stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_CREATION_AND_ASSIGNMENT] or stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_ASSIGNMENT]:
						variableName = None
						if stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_CREATION_AND_ASSIGNMENT]:
							variableName = re.findall(Patterns.VARIABLE_PATTERN, instruction)[1]
						elif stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_ASSIGNMENT]:
							variableName = re.findall(Patterns.VARIABLE_PATTERN, instruction)[0]

						variableName = self.aquireFullyQualifiedVariableName(variableName)


						if not variableName in self.knownLocalVariables or variableName in self.knownGlobalVariables:
							if stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_CREATION_AND_ASSIGNMENT]:
								self.createVariableAndAllocate(variableName)
							elif stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_ASSIGNMENT]:
								self.logCompilationError(lineCounter, "tried to assign number value to variable which does not exist!")
								continue
						elif (variableName in self.knownLocalVariables or variableName in self.knownGlobalVariables) and stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_CREATION_AND_ASSIGNMENT]:
							# variable is already defined ; log compiler error
							self.logCompilationError(lineCounter, "variable \"" + variableName + "\" is already defined!")
							continue

						assignmentValueInHex = "0" + hex(int(re.findall(r"\d+", instruction)[0]))[2:] + "h"
						self.assemblerLines.append("; " + instruction.replace("\t", ""))
						self.assemblerLines.append("mov dword ptr [ebp - " + self.retrieveStackPositionOfVariable(variableName) + "], " + assignmentValueInHex)
					
					# ----------------------------------------------------------------------------------------------------------------------
					elif stmPattern == self.statementPatterns[self.STRING_VARIABLE_CREATION_AND_ASSIGNMENT]:
						print(instruction)

					# ----------------------------------------------------------------------------------------------------------------------
					elif stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_VARIABLE_ASSIGNMENT] or stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_CREATION_AND_VARIABLE_ASSIGNMENT]:
						variableNames = None
						if stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_VARIABLE_ASSIGNMENT]:
							variableNames = re.findall(Patterns.VARIABLE_PATTERN, instruction)
						elif stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_CREATION_AND_VARIABLE_ASSIGNMENT]:
							variableNames = re.findall(Patterns.VARIABLE_PATTERN, instruction)[1:] # skip the first list entry ; would be "number"

						variableNames[0] = self.aquireFullyQualifiedVariableName(variableNames[0])
						variableNames[1] = self.aquireFullyQualifiedVariableName(variableNames[1])

						if stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_CREATION_AND_VARIABLE_ASSIGNMENT]:
							self.createVariableAndAllocate(variableNames[0])
						elif stmPattern == self.statementPatterns[self.NUMBER_VARIABLE_VARIABLE_ASSIGNMENT]:
							if (not (variableNames[0] in self.knownLocalVariables)) and (not (variableNames[0] in self.knownGlobalVariables)):
								self.logCompilationError(lineCounter, "cannot assign to unknown variable \"" + variableNames[0] + "\"!")
								continue

						if (not (variableNames[1] in self.knownLocalVariables)) and (not (variableNames[1] in self.knownGlobalVariables)):
							self.logCompilationError(lineCounter, "cannot assign value of unknown variable \"" + variableNames[1] + "\"!")
							continue
						if not self.knownVariablesTypes[variableNames[0]] == self.knownVariablesTypes[variableNames[1]]:
							self.logCompilationError(lineCounter, "assignment is only possible if both variables contain the same value type!")
							continue

						self.assemblerLines.append("; " + instruction.replace("\t", ""))
						self.assemblerLines.append("mov eax, dword ptr [ebp - " + self.retrieveStackPositionOfVariable(variableNames[1]) + "]")
						self.assemblerLines.append("mov dword ptr [ebp - " + self.retrieveStackPositionOfVariable(variableNames[0]) + "], eax")

					# ----------------------------------------------------------------------------------------------------------------------
					elif stmPattern == self.statementPatterns[self.IMPORT_STATEMENT]:
						# import the specified file and put it at the location of the import statement
						fileToImport = re.findall(r"\w+", instruction)[1]
						self.__importFile(fileToImport)

					# ----------------------------------------------------------------------------------------------------------------------
					elif stmPattern == self.statementPatterns[self.FUNCTION_STATEMENT]:
						if self.functionMode:
							self.logCompilationError(lineCounter, "Function boxing is not permitted! Compilation aborted!")
							break

						self.knownLocalVariables = {}

						self.functionMode = True
						self.functionPrecedingTabs = len(re.findall(r"\t", instruction))

						self.functionName = re.findall(Patterns.FUNCTION_STRING_PATTERN, instruction)[1]

						self.assemblerLines.append(self.functionName + " proc")

			lineCounter += 1

		# if after loop still in function mode than end the function properly
		if self.functionMode:
			self.assemblerLines.append("ret")
			self.assemblerLines.append(self.functionName + " endp")
			self.functionMode = False

	def __importFile(self, fileToImport):
			# seek the file relatively to the file which included the import statement
			fileToImportPath = self.filePath[0:self.filePath.rindex("\\") + 1] + fileToImport + "." + GeneralInfo.DEFAULT_FILE_EXTENSION
			#def __init__(self, filePath, assemblerLines = [], compilationErrors = [], knownVariables = {}, knownVariablesTypes = {}, bpOffset = 4):
			SimpleCompiler(fileToImportPath, self.assemblerLines, self.compilationErrors, self.knownLocalVariables, self.knownGlobalVariables, self.knownVariablesTypes, self.bpOffset)

	def __compileASMFile(self):

		baseInstructions = [".386",".model flat, stdcall", "option casemap: none", "include P:\masm32\include\kernel32.inc",
							"include P:\masm32\include\masm32.inc", "includelib P:\masm32\lib\kernel32.lib", "includelib P:\masm32\lib\masm32.lib"]

		file = open(self.filePath[0:self.filePath.rindex("\\") + 1] + self.fileName + "." + GeneralInfo.DEFAULT_FILE_EXTENSION + "." + GeneralInfo.ASM_FILE_EXTENSION, "a")
		
		for instruction in baseInstructions:
			file.write(instruction + "\n")

		file.write("\n.code\n")

		for instruction in self.assemblerLines:
			file.write(instruction + "\n")
		file.close()

compiler = SimpleCompiler("C:\\Users\\Sebastian\\Desktop\\test.simple")

for line in compiler.assemblerLines:
	print(line)

print()

if len(compiler.compilationErrors) == 0:
	print("No compilation errors occurred!")
else:
	print("Compilation erros listed underneath:\n")
	for error in compiler.compilationErrors:
		print(error)
