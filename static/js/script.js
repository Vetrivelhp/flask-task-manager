//Get elements from HTML
const create_tsk = document.getElementById("create_tsk");
const create_page = document.getElementById("create_page");
const all_tasks = document.getElementById("all_tasks");
		
let defaultState = "check_box_outline_blank";
let ongoingState = "indeterminate_check_box";
let completeState = "check_box";
	
//calling loading tasks functionfrom database
loadGroups();
		
//creating new task make page when click create button
create_tsk.addEventListener("click", () => {
	create_tsk.classList.add("pressed");

	setTimeout(() => {
		createNewTaskPage();
		create_tsk.classList.remove("pressed");
	}, 175);
});
		
function showDashboard() {
	create_page.style.display = "none";
	create_tsk.style.display = "block";
	all_tasks.style.display = "block";
}
		
function showEditor() {
	create_tsk.style.display = "none";
	all_tasks.style.display = "none";
	create_page.style.display ="flex";
}
		
function nextState(current) {
	if (current === 0) return 2;
	if (current === 2) return 1;
	return 0;
}
		
function setStateIcon(span, state, taskDiv) {
	if (state === 0) {
		span.textContent = defaultState;
		taskDiv.classList.remove("complete");
		taskDiv.classList.remove("ongoing");
		taskDiv.classList.add("default");
	}
	else if (state === 1) {
		span.textContent = completeState;
		taskDiv.classList.remove("default");
		taskDiv.classList.remove("ongoing");
		taskDiv.classList.add("complete");
	}
	else {
		span.textContent = ongoingState;
		taskDiv.classList.remove("complete");
		taskDiv.classList.remove("default");
		taskDiv.classList.add("ongoing");
	}
}
		
function collectTasks() {
    const task_items = create_page.querySelectorAll('.task-item');
    let task_arr = [];
    let index = 0;

    task_items.forEach(item => {
        const input = item.querySelector('.task-input');   // ← THIS WAS MISSING
        const state = parseInt(item.dataset.state) || 0;

        if (input.value.trim() !== "") {
            task_arr.push({
                id: item.dataset.taskId || null,
                client_id: item.dataset.clientId,
                parent_client_id: item.dataset.parentClientId || null,
                title: input.value.trim(),
                state: state,
                order_index: index++
            });
        }
    });

    return task_arr;
}
		
function createTaskElement(taskData = null, afterElement = null) {

	//creating seperate task inputs
	const taskDiv = document.createElement("div");
	taskDiv.className = "task-item";
	
	
	const clientId = (crypto.randomUUID)
		? crypto.randomUUID()
		: 'client-' + Date.now() + '-' + Math.random().toString(16).slice(2);
	taskDiv.dataset.clientId = taskData?.id ? `db-${taskData.id}` : clientId;	
				
	//Drag button
	const drag = document.createElement("button");
	drag.classList.add("drag");
	
	const drag_span = document.createElement("span");
	drag_span.className = "material-symbols-outlined";
	drag_span.textContent = 'drag_indicator';		
	drag.appendChild(drag_span);			

	const button = document.createElement("button");
	button.classList.add("state");
	const span = document.createElement("span");
	span.className = "material-symbols-outlined";
		
	//default state of task button
	let state = taskData ? taskData.state : 0;
	setStateIcon(span, state, taskDiv);
	
	taskDiv.dataset.state = state;
	
	button.appendChild(span);
			
	//creating task input
	const input = document.createElement("input");
	input.placeholder = "New task";
	input.className = "task-input";
	input.value = taskData ? taskData.title : "";
			
	// ID
	if (taskData && taskData.id) {
		taskDiv.dataset.taskId = taskData.id;
	}

	// PARENT
	if (taskData && taskData.parent_id) {
		taskDiv.dataset.parentId = taskData.parent_id;
		taskDiv.classList.add("child-task");
	}
			
	//adding task
	taskDiv.appendChild(drag);
	taskDiv.appendChild(button);
	taskDiv.appendChild(input);

	//changing state of task when clicked
	button.addEventListener("click", () => {
		state = nextState(state);
	    taskDiv.dataset.state = state;
		setStateIcon(span, state, taskDiv);
	});

	// ENTER key logic
	input.addEventListener("keydown", function (event) {
		if (event.key === "Enter") {
			event.preventDefault();
			addTask(taskDiv);			
		}
	});

	if (afterElement) {
		afterElement.insertAdjacentElement("afterend", taskDiv);
	} else {
		create_page.appendChild(taskDiv);
	}
			
	drag.addEventListener("click", () => {
		const previous = taskDiv.previousElementSibling;
		if (!previous) return;
		const isChild = taskDiv.classList.contains("child-task");
		if (isChild) {
			// Remove child
			taskDiv.classList.remove("child-task");
			taskDiv.classList.add("parent-task");
			delete taskDiv.dataset.parentId;
		} else {
			// Make child
			taskDiv.classList.remove("parent-task");
			taskDiv.classList.add("child-task");
			if (previous.dataset.clientId) {
				taskDiv.dataset.parentClientId = previous.dataset.clientId;
			} else {
				delete taskDiv.dataset.parentId;
			}
		}
	});	
	
	//remove empty task by backspace
	input.addEventListener("keydown", function (event) {
		if(input.value == "") {
			if(event.key === "Backspace") {
				const currentActiveElement = document.activeElement;
				if (currentActiveElement && currentActiveElement.classList.contains('task-input')) {
					const inputsArray = Array.from(create_page.querySelectorAll('.task-input'));
					const currentIndex = inputsArray.indexOf(currentActiveElement);
				    if (currentIndex > 0) {
						// Prevent default behavior to stop the character from being deleted after focus moves
						event.preventDefault();
						create_page.removeChild(taskDiv);
						inputsArray[currentIndex - 1].focus();
					}
					console.log(inputsArray);
					console.log(currentIndex);
				}
			}		
		}
	});
	return taskDiv;
}
		
//loading task groups from db
function loadGroups() {
	fetch("/api/groups") 
	.then(res => res.json())
	.then(groups => {
		all_tasks.innerHTML = "";
					
		const grid = document.createElement('div');
		grid.className = "task_grid";
		grid.classList.add("fade-in");

		//looping through all task groups
		groups.forEach(group => {
			const div = document.createElement('div');
			
			div.innerHTML = `		
						<h3>${group.title}</h3>
						<p>${group.description}</p>
						<small>${group.created_at}</small>			
			`;
			const card = document.createElement("div");
			
			div.addEventListener("click", () => {
				editTask(group.id, group.title, group.description);
			});
			
			const delButton = document.createElement("button");
			delButton.classList.add("delete");
			const delSpan = document.createElement("span");
			delSpan.className = "material-symbols-outlined";
			delSpan.textContent = "delete";
			delButton.appendChild(delSpan);
					
			delButton.addEventListener("click", (e) => {
				e.stopPropagation();
				deleteTask(group.id, card);
			});
			card.appendChild(div);
			card.appendChild(delButton);
			grid.appendChild(card);
								
		});						
		all_tasks.appendChild(grid);
		
		if (groups.length === 0) {
			const empty = document.createElement("div");
			empty.className = "empty-state fade-in";
			empty.innerHTML = `
				<div class="empty-icon"><img src="/static/images/cat.webp" alt="cat in box"></div>
				<h2>No Tasks Yet</h2>
				<p>Click the + button to create your first task group.</p>
			`;
			all_tasks.appendChild(empty);
			return;
		}
		
	});	
}
		
function deleteTask(id, element) {
    element.classList.add("card-removing");

    setTimeout(() => {
        fetch(`/api/delete/${id}`, { method: "DELETE" })
        .then(res => res.json())
        .then(data => loadGroups());
    }, 250);
}
		
function editTask(id, gtitle, gdescription, afterElement = null) {
	//hiding homepage and showing create task page
	showEditor();
	create_page.innerHTML = "";
	const title = document.createElement("input");
	title.placeholder = "Title";
	title.value = gtitle
	title.classList.add("td-input");
	title.classList.add("td-title");
	const description = document.createElement("input");
	description.placeholder = "Description";
	description.value = gdescription
	description.classList.add("td-input");
	description.classList.add("td-desc");
				
	create_page.appendChild(title);
	create_page.appendChild(description);
		
	fetch(`/api/tasks/${id}`)
	.then(res => res.json())
	.then(tasks => {
		tasks.forEach(task => {
			create_page.appendChild(createTaskElement(task));
		});
				
		const save_task = document.createElement("button");
		save_task.textContent = "Save";
		save_task.classList.add("save_button", "linux-btn");
		create_page.appendChild(save_task);	
			
		save_task.addEventListener("click", () => {
			const task_arr = collectTasks();
			//object with data to taskgroup table and task table
			let inputData = {
				title: title.value,
				description: description.value,
				task_list: task_arr,
			};	
			//sending data to store in db
			fetch(`/api/edit/${id}`, {
			method: "PATCH",
			headers: {
				"Content-Type": "application/json"
			},
			body: JSON.stringify(inputData) //converting to JSON
					
			})
			.then(res => res.json())
			.then(task => {
				console.log("Send", task)
				loadGroups(); 
			})			
			//Show homepage hide new task page elements
			showDashboard();		
			create_page.innerHTML = ""; //clear create page					
		});				

	});
}

//creating new task page
function createNewTaskPage() {
	//hiding homepage and showing create task page		
	showEditor();
			
	const title = document.createElement("input");
	title.placeholder = "Title";
	title.classList.add("td-input");
	title.classList.add("td-title");
	const description = document.createElement("input");
	description.placeholder = "Description";
	description.classList.add("td-input");
	description.classList.add("td-desc");
			
	create_page.appendChild(title);
	create_page.appendChild(description);

	addTask(); // create first task automatically
			
	const save_task = document.createElement("button");
	save_task.textContent = "Save";
	save_task.classList.add("save_button", "linux-btn");
	create_page.appendChild(save_task);
			
	function store_in_db() {
		const task_arr = collectTasks();
		//object with data to taskgroup table and task table
		let inputData = {
			title: title.value,
			description: description.value,
			task_list: task_arr,
		};		
		//sending data to store in db
		fetch("/api/create_task", {
		method: "POST",
		headers: {
			"Content-Type": "application/json"
		},
		body: JSON.stringify(inputData) //converting to JSON	
		})
		.then(res => res.json())
		.then(task => {
			console.log("Saved", task)
			loadGroups();
		})
	}

	//saving task when click save button
	save_task.addEventListener("click", () => {		
		store_in_db();
		//Show homepage hide new task page elements
		showDashboard();
		create_page.innerHTML = ""; //clear create page			
	});
}

function addTask(afterElement = null) {
	const newTask = createTaskElement();
	if (afterElement) {
		afterElement.insertAdjacentElement("afterend", newTask);
	} else {
		create_page.appendChild(newTask);
	}
	newTask.querySelector(".task-input").focus();	
}
		
function logout() {
	fetch("/logout")
	.then(res => res.json())
	.then(data => {
		if (data.success) {
			window.location.href = "/login";
		}
	});
}