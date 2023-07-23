import pyhop
import json

def check_enough (state, ID, item, num):
	if getattr(state,item)[ID] >= num: return []
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
		operation = f"op_{name.replace(' ', '_')}"

		requires = rule.get("Requires")
		if requires:
			requirement, amount = list(requires.items())[0]
			method_list.append(("have_enough", ID, requirement, amount))

		consumes = rule.get("Consumes")
		if consumes:
			for item, amount in consumes.items():
				method_list.append(("have_enough", ID, item, amount))

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

		for item, amount_produced in produces.items():
			current_amount = getattr(state, item, 0)[ID]
			setattr(state, item, {ID: current_amount + amount_produced})

		return state

	operator.__name__ = f"op_{name.replace(' ', '_')}"
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

	tools = data["Tools"]

	def heuristic (state, curr_task, tasks, plan, depth, calling_stack):
		method = curr_task[0]
		#print(f"current task: {curr_task}")
		print(f"current task: {curr_task}, calling stack: {calling_stack}")
		#print(f"tasks: {tasks}")
		#print(f"plan: {plan}")
		#print(f"method: {method}")
		if curr_task in calling_stack[1:] and method == "have_enough":
			print(f"\nreturning true because {curr_task} in calling stack\n")
			return True
		#if method == "produce":
		#	item = curr_task[2]
		#	if item in tools:
		#		return True

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

	state = set_up_state(data, 'agent', time=239) # allot time here
	goals = set_up_goals(data, 'agent')

	declare_operators(data)
	declare_methods(data)
	add_heuristic(data, 'agent')

	# pyhop.print_operators()
	# pyhop.print_methods()

	# Hint: verbose output can take a long time even if the solution is correct; 
	# try verbose=1 if it is taking too long
	pyhop.pyhop(state, goals, verbose=3)
	# pyhop.pyhop(state, [('have_enough', 'agent', 'cart', 1),('have_enough', 'agent', 'rail', 20)], verbose=3)
