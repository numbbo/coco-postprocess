function compareNumbers(a, b)
{ return a.val - b.val; }

function compareStrings(a, b)
{
	if (a.val < b.val) return -1;
	if (a.val > b.val) return +1;
	return 0;
}

function sortRows(rows, column)
{
	let numeric = true;
	let data = [];
	for (let tr of rows)
	{
		let cell = tr.children[column];
		if (! cell) continue;   // slightly better than stopping with an error
		let value = cell.getAttribute("sorttable_customkey");
		if (value === null) value = cell.innerText;
		if (Number.isNaN(Number.parseFloat(value))) numeric = false;
		data.push({val: value, row: tr});
	}
	let compare = numeric ? compareNumbers : compareStrings;
	data.sort(compare);
	return data;
}

window.addEventListener("load", function(event)
{
	let tables = document.querySelectorAll("table");
	for (let table of tables)
	{
		let cells = table.querySelectorAll("thead td, thead th");
		for (let column=0; column<cells.length; column++)
		{
			let cell = cells[column];
			cell.style.cursor = "pointer";
			cell.addEventListener("click", (event) =>
			{
				let rows = table.querySelectorAll("tbody tr");
				let data = sortRows(rows, column);
				let sameorder = true;
				let i = 0;
				for (let tr of rows)
				{
					if (data[i].row !== tr) sameorder = false;
					i++;
				}
				for (let table of tables)
				{
					let data = sortRows(table.querySelectorAll("tbody tr"), column);
					if (sameorder) data.reverse();
					for (let e of data) e.row.remove();
					let tbody = table.getElementsByTagName("tbody")[0];
					for (let e of data) tbody.appendChild(e.row);
				}
			});
		}
	}
});
