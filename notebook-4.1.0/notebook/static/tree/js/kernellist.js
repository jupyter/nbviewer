// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

define([
    'base/js/namespace',
    'jquery',
    'tree/js/notebooklist',
], function(IPython, $, notebooklist) {
    "use strict";

    var KernelList = function (selector, options) {
        /**
         * Constructor
         *
         * Parameters:
         *  selector: string
         *  options: dictionary
         *      Dictionary of keyword arguments.
         *          session_list: SessionList instance
         *          base_url: string
         *          notebook_path: string
         */
        notebooklist.NotebookList.call(this, selector, $.extend({
            element_name: 'running'},
            options));
        this.kernelspecs = this.sessions = null;
        this.events.on('kernelspecs_loaded.KernelSpec', $.proxy(this._kernelspecs_loaded, this));
    };

    KernelList.prototype = Object.create(notebooklist.NotebookList.prototype);

    KernelList.prototype.add_duplicate_button = function () {
        /**
         * do nothing
         */
    };
    
    KernelList.prototype._kernelspecs_loaded = function (event, kernelspecs) {
        this.kernelspecs = kernelspecs;
        if (this.sessions) {
            // trigger delayed session load, since kernelspecs arrived later
            this.sessions_loaded(this.sessions);
        }
    };
    
    KernelList.prototype.sessions_loaded = function (d) {
        this.sessions = d;
        if (!this.kernelspecs) {
            return; // wait for kernelspecs before first load
        }
        this.clear_list();
        var item, path, session;
        for (path in d) {
            if (!d.hasOwnProperty(path)) {
                // nothing is safe in javascript
                continue;
            }
            session = d[path];
            item = this.new_item(-1);
            this.add_link({
                name: path,
                path: path,
                type: 'notebook',
                kernel_display_name: this.kernelspecs[session.kernel.name].spec.display_name
            }, item);
        }
        $('#running_list_placeholder').toggle($.isEmptyObject(d));
    };

    KernelList.prototype.add_link = function (model, item) {
        notebooklist.NotebookList.prototype.add_link.apply(this, [model, item]);

        var running_indicator = item.find(".item_buttons")
            .text('');

        var that = this;
        var kernel_name = $('<div/>')
            .addClass('kernel-name')
            .text(model.kernel_display_name)
            .appendTo(running_indicator);

        var shutdown_button = $('<button/>')
            .addClass('btn btn-warning btn-xs')
            .text('Shutdown')
            .click(function() {
                var path = $(this).parent().parent().parent().data('path');
                that.shutdown_notebook(path);
            })
            .appendTo(running_indicator);
    };
    
    // Backwards compatability.
    IPython.KernelList = KernelList;

    return {'KernelList': KernelList};
});
