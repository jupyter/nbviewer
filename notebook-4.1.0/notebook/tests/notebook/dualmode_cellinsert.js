
// Test
casper.notebook_test(function () {
    var a = 'print("a")';
    var index = this.append_cell(a);
    this.execute_cell_then(index);

    var b = 'print("b")';
    index = this.append_cell(b);
    this.execute_cell_then(index);

    var c = 'print("c")';
    index = this.append_cell(c);
    this.execute_cell_then(index);
    
    this.thenEvaluate(function() {
        IPython.notebook.default_cell_type = 'code';
    });
    
    this.then(function () {
        // Cell insertion
        this.select_cell(2);
        this.trigger_keydown('m'); // Make it markdown
        this.trigger_keydown('a'); // Creates one cell
        this.test.assertEquals(this.get_cell_text(2), '', 'a; New cell 2 text is empty');
        this.test.assertEquals(this.get_cell(2).cell_type, 'code', 'a; inserts a code cell');
        this.validate_notebook_state('a', 'command', 2);
        this.trigger_keydown('b'); // Creates one cell
        this.test.assertEquals(this.get_cell_text(2), '', 'b; Cell 2 text is still empty');
        this.test.assertEquals(this.get_cell_text(3), '', 'b; New cell 3 text is empty');
        this.test.assertEquals(this.get_cell(3).cell_type, 'code', 'b; inserts a code cell');
        this.validate_notebook_state('b', 'command', 3);
    });
    
    this.thenEvaluate(function() {
        IPython.notebook.class_config.set('default_cell_type', 'selected');
    });
    
    this.then(function () {
        this.select_cell(2);
        this.trigger_keydown('m'); // switch it to markdown for the next test
        this.test.assertEquals(this.get_cell(2).cell_type, 'markdown', 'test cell is markdown');
        this.trigger_keydown('a'); // new cell above
        this.test.assertEquals(this.get_cell(2).cell_type, 'markdown', 'a; inserts a markdown cell when markdown selected');
        this.trigger_keydown('b'); // new cell below
        this.test.assertEquals(this.get_cell(3).cell_type, 'markdown', 'b; inserts a markdown cell when markdown selected');
    });
    
    this.thenEvaluate(function() {
        IPython.notebook.class_config.set('default_cell_type', 'above');
    });
    
    this.then(function () {
        this.select_cell(2);
        this.trigger_keydown('y'); // switch it to code for the next test
        this.test.assertEquals(this.get_cell(2).cell_type, 'code', 'test cell is code');
        this.trigger_keydown('b'); // new cell below
        this.test.assertEquals(this.get_cell(3).cell_type, 'code', 'b; inserts a code cell below code cell');
        this.trigger_keydown('a'); // new cell above
        this.test.assertEquals(this.get_cell(3).cell_type, 'code', 'a; inserts a code cell above code cell');
    });
    
    this.then(function () {
        this.set_cell_text(1, 'cell1');
        this.select_cell(1);
        this.select_cell(2, false);
        this.trigger_keydown('a');
        this.test.assertEquals(this.get_cell_text(1), '', 'a; New cell 1 text is empty');
        this.test.assertEquals(this.get_cell_text(2), 'cell1', 'a; Cell 2 text is old cell 1');
        
        this.set_cell_text(1, 'cell1');
        this.set_cell_text(2, 'cell2');
        this.set_cell_text(3, 'cell3');
        this.select_cell(1);
        this.select_cell(2, false);
        this.trigger_keydown('b');
        this.test.assertEquals(this.get_cell_text(1), 'cell1', 'b; Cell 1 remains');
        this.test.assertEquals(this.get_cell_text(2), 'cell2', 'b; Cell 2 remains');
        this.test.assertEquals(this.get_cell_text(3), '', 'b; Cell 3 is new');
        this.test.assertEquals(this.get_cell_text(4), 'cell3', 'b; Cell 4 text is old cell 3');
    });
});
