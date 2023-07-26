import pyhop
import json
"""
import #logging, traceback, sys, os, inspect
#logging.basicConfig(filename=__file__[:-3] +'.log', filemode='w', level=#logging.DEBUG)
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
"""
tools = []

def get_material(tool):
	if "wood" in tool:
		return "wood"
	elif "stone" in tool:
		return "stone"
	elif "iron" in tool:
		return "iron"
	return None

def get_tool(tool):
	if "pickaxe" in tool:
		return "pickaxe"
	elif "axe" in tool:
		return "axe"
	return None

def check_enough (state, ID, item, num):
	if getattr(state,item)[ID] - state.claimed_items.get(item, 0) >= num:
		if item not in tools:
			if item in state.claimed_items:
				state.claimed_items[item] += num
			else:
				state.claimed_items[item] = num
			##logging.debug(f"claiming {num} of {item}")
		return []
	return False

def produce_enough (state, ID, item, num):
	return [('produce', ID, item), ('have_enough', ID, item, num)]

pyhop.declare_methods ('have_enough', check_enough, produce_enough)

def produce (state, ID, item):
	return [('produce_{}'.format(item), ID)]

pyhop.declare_methods ('produce', produce)

def make_method (name, rule):
	#print(f"name: {name}, rule: {rule}")
	def method (state, ID):
		method_list = []
		item_consumptions = {}

		requires = rule.get("Requires")
		if requires:
			requirement, amount = list(requires.items())[0]
			method_list.append(("have_enough", ID, requirement, amount))

		consumes = rule.get("Consumes")
		if consumes:
			for item, amount in consumes.items():
				item_consumptions[item] = amount
				if requires:
					method_list.insert(1, ("have_enough", ID, item, amount))
				else:
					method_list.insert(0, ("have_enough", ID, item, amount))

		operation = f"op_{name.replace(' ', '_')}"
		method_list.append((operation, ID))
		return method_list

	method.__name__ = f"{name.replace(' ', '_')}"
	return method

def declare_methods (data):
	# some recipes are faster than others for the same product even though they might require extra tools
	# sort the recipes so that faster recipes go first
	recipes = data["Recipes"]

	product_recipes = {}
	for key, value in recipes.items():
		product = list(value["Produces"])[0]
		if product in product_recipes:
			product_recipes[product].append((key, value))
		else:
			product_recipes[product] = [(key, value)]

	for product, recipeList in product_recipes.items():
		methods = []
		times = {}
		for recipe in recipeList:
			time = recipe[1]["Time"]
			method = make_method(recipe[0], recipe[1])
			methods.append(method)
			times[method] = time

		methods.sort(key=lambda x: times[x])

		pyhop.declare_methods(f"produce_{product}", *methods)
	#print(data)
	#for key, value in recipes.items():
	#	methods.append(make_method(key, value))
	#pyhop.declare_methods(*methods)

	# your code here
	# hint: call make_method, then declare the method to pyhop using pyhop.declare_methods('foo', m1, m2, ..., mk)

def make_operator (rule):
	name = rule[0]
	recipe = rule[1]

	requires = recipe.get("Requires")
	produces = recipe.get("Produces")
	consumes = recipe.get("Consumes")
	operation_name = f"op_{name.replace(' ', '_')}"
	def operator (state, ID):
		time = recipe["Time"]
		if state.time[ID] < time:
			return False
		state.time = {ID: state.time[ID] - time}

		if requires:
			for item, amount_needed in requires.items():
				curr_requirement_count = getattr(state, item, 0)[ID]
				if curr_requirement_count < amount_needed:
					return False

		if consumes:
			for item, amount_needed in consumes.items():
				current_amount = getattr(state, item, None)[ID]
				if amount_needed > current_amount:
					return False
				setattr(state, item, {ID: current_amount - amount_needed})
				state.claimed_items[item] -= amount_needed
				#logging.debug(f"unclaiming {amount_needed} of {item}")

		for item, amount_produced in produces.items():
			current_amount = getattr(state, item, 0)[ID]
			setattr(state, item, {ID: current_amount + amount_produced})

		return state

	operator.__name__ = operation_name
	return operator

def declare_operators (data):
	operators = []
	recipes = data["Recipes"]
	for item in recipes.items():
		operators.append(make_operator(item))
	# hint: call make_operator, then declare the operator to pyhop using pyhop.declare_operators(o1, o2, ..., ok)
	pyhop.declare_operators(*operators)

def add_heuristic (data, ID):
	# prune search branch if heuristic() returns True
	# do not change parameters to heuristic(), but can add more heuristic functions with the same parameters:
	# e.g. def heuristic2(...); pyhop.add_check(heuristic2)

	def simple_heuristic(state, curr_task, tasks, plan, depth, calling_stack):
		method = curr_task[0]
		#logging.debug(f"\n\ncurrent task: {curr_task}")

		if method == "produce":
			item = curr_task[2]
			if item in tools:
				operation_string = f"op_craft_{item}"
				#logging.debug(f"operation string: {operation_string}")
				for task in tasks[1:]:
					#logging.debug(f"task: {task[0]}")
					if operation_string in task[0]:
						#logging.debug(f"canceling because {curr_task} already in tasks")
						return True
		"""if method == "have_enough" and len(tasks) > 2:
			wood_pickaxe_occurrences = 0
			for task in tasks:
				if task[0] == "have_enough" and task[2] == "wooden_pickaxe":
					wood_pickaxe_occurrences += 1
			impetus_action = tasks[2]
			#logging.debug(f"impetus action: {impetus_action}, pickaxe count: {wood_pickaxe_occurrences}")
			if wood_pickaxe_occurrences >= 2 and impetus_action[0] == "have_enough" and impetus_action[2] == "wood":
				#logging.debug("forcing punch")
				return True"""

		return False

	def heuristic (state, curr_task, tasks, plan, depth, calling_stack):
		method = curr_task[0]
		#logging.debug(f"\ncurrent task: {curr_task}\n calling stack: {calling_stack}\n tasks: {tasks}\n plan: {plan}")

		if method == "produce":
			item = curr_task[2]
			current_amount_of_item = getattr(state, item, 0)[ID]
			#logging.debug(f"item: {item}, has: {current_amount_of_item}")
			#print(f"item: {item}, has: {current_amount_of_item}")
			if item in tools:
				if current_amount_of_item > 0:
					#logging.debug(f"already got tool {item}")
					return True
				material_type = get_material(item)

				if material_type is not None:
					tool_type = get_tool(item)
					#if tool_type == "pickaxe":
					if (state.tool_level_requirement == "stone" or state.tool_level_requirement == "iron") and getattr(state, f"wooden_{tool_type}", 0)[ID] == 0 and material_type != "wood":
						#logging.debug(f"canceling {item} because wood {tool_type} needed first")
						return True
					elif state.tool_level_requirement == "iron" and getattr(state, f"stone_{tool_type}", 0)[ID] == 0 and material_type != "stone" and material_type != "wood":
						#logging.debug(f"canceling {item} because stone {tool_type} needed first")
						return True

		elif method == "have_enough" and curr_task[2] in tools:
			if curr_task in tasks[1:]:
				#logging.debug(f"\nreturning true because {curr_task} in tasks\n")
				#print(f"\nreturning true because {curr_task} in tasks\n")
				return True
			tool = curr_task[2]
			material_type = get_material(tool)

			if material_type is not None and len(tasks) > 2:
				if len(tasks) > 2:
					impetus_task = tasks[2]
					#logging.debug(f"impetus task: {impetus_task}")
					if impetus_task[0] == "have_enough" and impetus_task[2] == "wood" and ((getattr(state, "wooden_axe", 0)[ID] > 0 and material_type != "wood") or
																						   (getattr(state, "stone_axe", 0)[ID] > 0 and material_type != "stone")):
						#logging.debug("canceling and using weaker axe instead")
						return True
					elif impetus_task[0] == "have_enough" and impetus_task[2] == "cobble" and ((getattr(state, "wooden_pickaxe", 0)[ID] > 0 and material_type != "wood") or
																						   (getattr(state, "stone_pickaxe", 0)[ID] > 0 and material_type != "stone")):
						#logging.debug("canceling and using weaker pickaxe instead")
						return True
					elif impetus_task[0] == "have_enough" and impetus_task[2] == "ore" and getattr(state, "stone_pickaxe", 0)[ID] > 0 and material_type != "stone":
						#logging.debug("canceling and using weaker pickaxe instead")
						return True

				if state.tool_level_requirement is None:
					state.tool_level_requirement = material_type
				elif state.tool_level_requirement == "stone" and material_type == "iron" or (state.tool_level_requirement == "wood" and material_type != "wood"):
					#logging.debug(f"not creating {tool} because material is unnecessary")
					return True

		return False # if True, prune this branch

	pyhop.add_check(heuristic)


def set_up_state (data, ID, time=0):
	state = pyhop.State('state')
	state.time = {ID: time}

	for item in data['Items']:
		setattr(state, item, {ID: 0})

	for item in data['Tools']:
		setattr(state, item, {ID: 0})

	for item, num in data['Initial'].items():
		setattr(state, item, {ID: num})

	return state

def set_up_goals (data, ID):
	goals = []
	for item, num in data['Goal'].items():
		goals.append(('have_enough', ID, item, num))

	return goals

if __name__ == '__main__':
	rules_filename = 'crafting.json'

	with open(rules_filename) as f:
		data = json.load(f)

	state = set_up_state(data, 'agent', time=46) # allot time here
	goals = set_up_goals(data, 'agent')

	tools = data["Tools"]

	declare_operators(data)
	declare_methods(data)
	add_heuristic(data, 'agent')
	state.claimed_items = {}
	state.tool_level_requirement = None

	# pyhop.print_operators()
	# pyhop.print_methods()

	# Hint: verbose output can take a long time even if the solution is correct; 
	# try verbose=1 if it is taking too long
	pyhop.pyhop(state, goals, verbose=1)
