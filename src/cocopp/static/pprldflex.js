"use strict";

const dom = {};       // shortcut access to HTML elements
const history = [];   // very short state history
const columns_selected = {dim: 4, func: 1};   // number of columns per display type

// fill the dimension into a filename template
function filename(template, dimension)
{
	let start = template.indexOf("<");
	if (start < 0) return template;
	start++;
	let end = template.indexOf(">", start);
	if (end < 0) throw new Error("invalid filename template '" + template + "'");
	let strdim = "" + dimension;
	if (end > start)
	{
		if (template[start + 1] !== ",") throw new Error("invalid filename template '" + template + "'");
		let c = template[start];
		let w = parseInt(template[start + 2]);
		while (strdim.length < w) strdim = c + strdim;
	}
	let result = template.substring(0, start - 1) + strdim + template.substring(end + 1);
	return result;
}

// create DOM element
function createElement(description)
{
	let element = document.createElement(description.type);

	// set classes
	if (description.classname) element.className = description.classname;

	// set ID
	if (description.hasOwnProperty("id")) element.id = description.id;

	// add properties to the element
	if (description.hasOwnProperty("properties"))
	{
		for (let key in description.properties)
		{
			if (! description.properties.hasOwnProperty(key)) continue;
			element[key] = description.properties[key];
		}
	}

	// apply styles
	if (description.hasOwnProperty("style"))
	{
		for (let key in description.style)
		{
			if (! description.style.hasOwnProperty(key)) continue;
			element.style[key] = description.style[key];
		}
	}

	// add inner text
	if (description.hasOwnProperty("text")) element.appendChild(document.createTextNode(description.text));

	// add inner html
	if (description.hasOwnProperty("html")) element.innerHTML += description.html;

	// add a click handler
	if (description.hasOwnProperty("click"))
	{
		element.addEventListener("click", description.click);
		element.classList.add("clickable");
	}

	// add arbitrary event handlers
	if (description.hasOwnProperty("events"))
	{
		for (let key in description.events)
		{
			if (! description.events.hasOwnProperty(key)) continue;
			element.addEventListener(key, description.events[key]);
		}
	}

	// add to a parent
	if (description.parent) description.parent.appendChild(element);

	return element;
}

// build everything that goes into the content section
function buildContent(event)
{
	let dim_index = dom.cur_dim.selectedIndex;
	let func_index = dom.cur_func.selectedIndex;

	if (history[history.length-1].dim !== dim_index || history[history.length-1].func != func_index)
	{
		history.push({ dim: dim_index, func: func_index});
		while (history.length > 2) history.shift();
	}

	let old = [];
	for (let e of dom.content.children)
	{
		if (e.nodeName === "TABLE" || e.nodeName === "IMG") old.push(e);
		else e.remove();
	}

	if (dom.type.selectedIndex === 0)
	{
		// per dimension
		dom.cur_dim.disabled = false;
		dom.inc_dim.disabled = false;
		dom.dec_dim.disabled = false;
		dom.cur_func.disabled = true;
		dom.inc_func.disabled = true;
		dom.dec_func.disabled = true;
		dom.columns.disabled = false;
		dom.columns.selectedIndex = columns_selected.dim;

		let cols = [2,3,4,5,6,8,10][columns_selected.dim];
		let colwidth = (99 / cols) + "vw";

		let table = createElement({type: "table", parent: dom.content, classname: "all_functions"});
		let j = 0;
		let tr = null;
		for (let i=0; i<config.functions.length; i++)
		{
			if (j === 0) tr = createElement({type: "tr", parent: table});
			let td = createElement({type: "td", parent: tr});
			let src = filename(config.functions[i].filename, config.dimensions[dim_index]);
			let img = createElement({type: "img", parent: td, style: {width: colwidth}, properties: {src: src}, click: (event) =>
			{
				dom.type.selectedIndex = 2;
				dom.cur_func.selectedIndex = i;
				buildContent();
			}});
			j = (j + 1) % cols;
		}
	}
	else if (dom.type.selectedIndex === 1)
	{
		// per function
		dom.cur_dim.disabled = true;
		dom.inc_dim.disabled = true;
		dom.dec_dim.disabled = true;
		dom.cur_func.disabled = false;
		dom.inc_func.disabled = false;
		dom.dec_func.disabled = false;
		dom.columns.disabled = false;
		dom.columns.selectedIndex = columns_selected.func;

		let cols = [2,3,4,5,6,8,10][columns_selected.func];
		let colwidth = (99 / cols) + "vw";

		let table = createElement({type: "table", parent: dom.content, classname: "per_function"});
		let j = 0;
		let tr = null;
		for (let i=0; i<config.dimensions.length; i++)
		{
			if (j === 0) tr = createElement({type: "tr", parent: table});
			let td = createElement({type: "td", parent: tr});
			let src = filename(config.functions[func_index].filename, config.dimensions[i]);
			let img = createElement({type: "img", parent: td, style: {width: colwidth}, properties: {src: src}, click: (event) =>
			{
				dom.type.selectedIndex = 2;
				dom.cur_dim.selectedIndex = i;
				buildContent();
			}});
			j = (j + 1) % cols;
		}
	}
	else if (dom.type.selectedIndex === 2)
	{
		// single plot
		dom.cur_dim.disabled = false;
		dom.inc_dim.disabled = false;
		dom.dec_dim.disabled = false;
		dom.cur_func.disabled = false;
		dom.inc_func.disabled = false;
		dom.dec_func.disabled = false;
		dom.columns.disabled = true;

		let src = filename(config.functions[func_index].filename, config.dimensions[dim_index]);
		let img = createElement({type: "img", parent: dom.content, classname: "single_plot", properties: {src: src}});
	}
	else throw new Error("unknown type");

//	createElement({type: "p", parent: dom.content, html: "Bootstrapped empirical cumulative distribution of the number of f-evaluations divided by dimension (FEvals/DIM) for 51 targets with target precision in <i>10<sup>-8..2</sup></i> for all functions and subgroups in different dimensions. As reference algorithm, the best algorithm from BBOB 2009 is shown as light thick line with diamond markers."});

	window.setTimeout(() => dom.content.focus(), 10);

	console.log("old", old);
	window.setTimeout(() => { for (let e of old) e.remove(); }, 250);
}

// entry point
window.addEventListener("load", function(event)
{
	// easy DOM access
	for (let id of ["header", "content", "type", "func", "cur_func", "dec_func", "inc_func", "dim", "cur_dim", "dec_dim", "inc_dim", "columns"])
	{
		dom[id] = document.querySelector("#" + id);
	}

	// prepare the header controls
	for (let f of config.functions) createElement({type: "option", parent: dom.cur_func, properties: {name: f.name}, text: f.name});
	for (let d of config.dimensions) createElement({type: "option", parent: dom.cur_dim, properties: {name: d}, text: d});
	history.push({dim: config.dimensions.length >= 5 ? 4 : 0, func: 0});
	dom.cur_func.selectedIndex = history[0].func;
	dom.cur_dim.selectedIndex = history[0].dim;

	// add initial page content
	buildContent();

	// handle events
	function prevDim(event)
	{
		let s = dom.content.scrollTop;
		dom.cur_dim.selectedIndex = (dom.cur_dim.selectedIndex + config.dimensions.length - 1) % config.dimensions.length;
		buildContent();
		dom.content.scrollTop = s;
		window.setTimeout(() => dom.content.scrollTop = s, 1);
	}
	function nextDim(event)
	{
		let s = dom.content.scrollTop;
		dom.cur_dim.selectedIndex = (dom.cur_dim.selectedIndex + 1) % config.dimensions.length;
		buildContent();
		dom.content.scrollTop = s;
		window.setTimeout(() => dom.content.scrollTop = s, 1);
	}
	function prevFunc(event)
	{
		let s = dom.content.scrollTop;
		dom.cur_func.selectedIndex = (dom.cur_func.selectedIndex + config.functions.length - 1) % config.functions.length;
		buildContent();
		dom.content.scrollTop = s;
		window.setTimeout(() => dom.content.scrollTop = s, 1);
	}
	function nextFunc(event)
	{
		let s = dom.content.scrollTop;
		dom.cur_func.selectedIndex = (dom.cur_func.selectedIndex + 1) % config.functions.length;
		buildContent();
		dom.content.scrollTop = s;
		window.setTimeout(() => dom.content.scrollTop = s, 1);
	}

	dom.type.addEventListener("change", buildContent);
	dom.cur_dim.addEventListener("change", buildContent);
	dom.dec_dim.addEventListener("click", prevDim);
	dom.inc_dim.addEventListener("click", nextDim);
	dom.cur_func.addEventListener("change", buildContent);
	dom.dec_func.addEventListener("click", prevFunc);
	dom.inc_func.addEventListener("click", nextFunc);

	dom.columns.addEventListener("change", function(event)
	{
		if (dom.type.selectedIndex === 0) columns_selected.dim = dom.columns.selectedIndex;
		else if (dom.type.selectedIndex === 1) columns_selected.func = dom.columns.selectedIndex;
		buildContent();
	});

	window.addEventListener("keydown", function(event)
	{
		let consumed = true;
		if (event.key === " ")
		{
			// toggle current and previous setting
			let n = history.length;
			if (n < 2) return;
			let old = history[n - 2];
			dom.cur_dim.selectedIndex = old.dim;
			dom.cur_func.selectedIndex = old.func;
			buildContent();
		}
		else if (event.key === "1") { dom.type.selectedIndex = 0; buildContent(); }
		else if (event.key === "2") { dom.type.selectedIndex = 1; buildContent(); }
		else if (event.key === "3") { dom.type.selectedIndex = 2; buildContent(); }
		else if (event.key === "ArrowUp") prevDim();
		else if (event.key === "ArrowDown") nextDim();
		else if (event.key === "ArrowLeft") prevFunc();
		else if (event.key === "ArrowRight") nextFunc();
		else consumed = false;

		if (consumed)
		{
			event.preventDefault();
			event.stopPropagation();
		}
	});

	// pre-load all images
	let images = [];
	for (let func of config.functions)
	{
		for (let dim of config.dimensions)
		{
			images.push(filename(func.filename, dim));
		}
	}
	function load()
	{
		if (images.length === 0) return;
	    let img = new Image();
	    img.src = images.pop();
	    window.setTimeout(load, 1);
	}
	load();
});
