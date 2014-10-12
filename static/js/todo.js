
$(document).ready(function() {

    $.fn.editable.defaults.mode = 'inline';
    $.fn.editable.defaults.ajaxOptions = {type: "GET"};

    var ws = new WebSocket("ws://localhost:8080/websocket");
    ws.onopen = function() {
        ws.send("Hello, world");
    };

    ws.onmessage = function (evt) {
        if (evt.data == 'update') {
            reload()
        }
    };

    reload = function() {
        refreshList();
        refreshContexts();
        refreshProjects();
    };

    refreshList = function() {
        $.ajax({
            url:    '/list/get',
            success:    function(data) {
                $('#todo-list').replaceWith(data);
                live();
                $('.link-action').hide();
            }
        });
    };

    refreshContexts = function() {
        $.ajax({
            url:    '/contexts/get',
            success:    function(data) {
                $('#contexts').replaceWith(data);
                live();
            }
        });
    };

    refreshProjects = function() {
        $.ajax({
            url:    '/projects/get',
            success:    function(data) {
                $('#projects').replaceWith(data);
                live();
            }
        });
    };

    function extractor(query) {
        var result = /([^ ]+)$/.exec(query);
        if(result && result[1])
            return result[1].trim();
        return '';
    }

    typeaheadoptions = {
        source: function() {
            data = []
            $('#projects span.project, #contexts span.context').each(function(item) {
                data.push($(this).data('value'));
            })
            return data;
        },
        updater: function(item) {
            return this.$element.val().replace(/[^\ ]*$/,'')+item;
        },
        matcher: function (item) {
          var tquery = extractor(this.query);
          if(!tquery) return false;
          return ~item.toLowerCase().indexOf(tquery.toLowerCase())
        },
        highlighter: function (item) {
          var query = extractor(this.query).replace(/[\-\[\]{}()*+?.,\\\^$|#\s]/g, '\\$&')
          return item.replace(new RegExp('(' + query + ')', 'ig'), function ($1, match) {
            return '<strong>' + match + '</strong>'
          })
        }
    }

    $('.link-action').hide();

    new_options = {
        inputclass: 'todoinput',
        clear: false,
        showbuttons: false,
        //type: 'text',
        pk:     function() {
            return 'pk';
        },
        url:    '/api/new',
        params: function(params) {
            return { data: params.value };
        },
        value: '',
        source: [ 
            { value: 'aa', text: 'AA' },
            { value: 'bb', text: 'BB' },
        ],
        success: function(response, newValue) {
            reload();
        },
    };
        
    edit_options = {
        inputclass: 'todoinput',
        clear: false,
        showbuttons: false,
        //type: 'text',
        pk:     function() {
            return 'pk';
        },
        //url:    '/api/new',
        url:    function(params) {
            var d = new $.Deferred;

            line = $(this).data('line');
            hash = $(this).data('hash');
            $.ajax({
                url:    '/api/edit/' + line + '/' + hash,// + '/' + encodeURIComponent(value),
                data:   {
                    data: params.data
                },
                success:    function(data) {
                    d.resolve();
                }
            });

            return d.promise();
        },
        submit: function(options) {
            console.info(options);
        },
        params: function(params) {
            return { data: params.value };
        },
        success: function(response, newValue) {
            reload();
        },
    };

    live = function() {
        $('#todo-new').editable(new_options);
        $('.todo:not(#todo-new)').editable(edit_options);

        $('#todo-new, .todo:not(#todo-new)').on('shown', function(e, editable) {
            $(editable.input.$input).typeahead(typeaheadoptions);
        });

        $('.todo a').click(function() {
            window.location = $(this).attr('href');
            return false;
        });

        highlight();
    };

    $('#todo-content').on('mouseenter', '#todo-list li', function() {
        $(this).children('.link-action').show();
    });

    $('#todo-content').on('mouseleave', '#todo-list li', function() {
        $(this).children('.link-action').hide();
    });

    $('#projects a').click(function(e) {
        filterUrl = '/filter/';
        filter = $(this).find('span').data('value');

        if (e.ctrlKey) {
            isFilterUrl = window.location.pathname.substr(0, filterUrl.length) == filterUrl;
            if (isFilterUrl) {
                // Remove filter
                pos = window.location.pathname.indexOf(filter)
                if (pos > 0) {
                    path = window.location.pathname;
                    path = path.substr(0, pos) + path.substr(pos + filter.length);
                    window.location = path;
                } else {
                    window.location += filter;
                }
            }

            return false;
        }
    });

    highlight = function() {
        $('#todo-content, #projects, #contexts').on('mouseenter', '.context, .project', function() {
            $('.' + $(this).data('type') + '-' + $(this).data('value').substr(1)).addClass('highlight');
        });
        
        $('#todo-content, #projects, #contexts').on('mouseleave', '.context, .project', function() {
            $('.' + $(this).data('type') + '-' + $(this).data('value').substr(1)).removeClass('highlight');
        });
    };

    highlight();

    getRoot = function() {
        return '/' + ($('#todo-selector').find(":selected").val());
    };

    $('#todo-content').on('click', '.link-delete', function(e) {
        if (confirm('Are you sure ?')) {
            line = $('#todo-' + $(this).data('line')).data('line');
            hash = $('#todo-' + $(this).data('line')).data('hash');

            e.preventDefault();
            e.stopPropagation();

            $.ajax({
                url:    '/delete/' + line + '/' + hash,
                success:    function(data) {
                    reload()
                }
            });
        }

        return false;
    });

    /*
    $('#todo-content').on('click', '.link-done', function(e) {
        if (confirm('Are you sure ?')) {
            line = $('#todo-' + $(this).data('line')).data('line');
            hash = $('#todo-' + $(this).data('line')).data('hash');

            e.preventDefault();
            e.stopPropagation();

            $.ajax({
                url:    '/mark_as_done/' + line + '/' + hash,
                success:    function(data) {
                    reload()
                }
            });
        }

        return false;
    });
    */

    var undos = []

    $('#todo-content').on('click', '.link-done', function(e) {
        $(this).hide();
        $(this).parent('li').addClass('deleted');
        $(this).parent('li').find('.link-undo, .link-undo span').show();

        var line = $('#todo-' + $(this).data('line')).data('line');
        var hash = $('#todo-' + $(this).data('line')).data('hash');

        undos[line] = setTimeout(function() {

            $('#line-' + line).hide('slow', function() {

                e.preventDefault();
                e.stopPropagation();

                $.ajax({
                    url:    '/mark_as_done/' + line + '/' + hash,
                    success:    function(data) {
                        reload()
                    }
                });

            });
        }, 3000);

        return false;
    });

    $('#todo-content').on('click', '.link-undo', function(e) {
        var line = $('#todo-' + $(this).data('line')).data('line');
        clearTimeout(undos[line]);

        //$(this).hide();
        $(this).parent('li').removeClass('deleted');
        $(this).parent('li').find('.link-undo, .link-undo span').hide();
    });

    $('#todo-selector').change(function() {
        window.location = '/' + $(this).val() + '/';
    });


    live();
});
