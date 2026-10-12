this.ckan.module('citeproc-modal', function($){
  return {
    /* options object can be extended using data-module-* attributes */
    options : {
      ajax_uri: null,
    },
    initialize: function (){
      const _ = this._;

      function build_cite_section(index, citation){
        let title = citation.type;
        if( citation.type_acronym ){
          title += '&nbsp;<strong>(' + citation.type_acronym + ')</strong>';
        }
        let html = '<div class="accordion-item">';
        html += '<h2 class="accordion-heading">';
        html += '<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-citeproc-' + index + '" aria-expanded="false" aria-controls="collapse-citeproc-' + index + '">' + title + '</button>';
        html += '</h2>';
        html += '<div id="collapse-citeproc-' + index + '" class="accordion-collapse collapse" aria-labelledby="collapse-citeproc-' + index + '" data-bs-parent="#citeproc-accordion">';
        html += '<div class="accordion-body"><div class="citeproc-citation-wrapper">';
        html += '<pre class="citeproc-citation-content">' + citation.citation + '</pre>';
        if( navigator.clipboard ){
          html += '<button class="btn btn-secondary citeproc-copy-bttn" title="' + _("Copy to clipboard") + '" aria-label="' + _("Copy to clipboard") + '" class="btn btn-secondary float-right float-end"><i aria-hidden="true" class="far fa-copy"></i></button>';
        }
        html += '</div></div></div></div>';
        return html;
      }

      function build_content(data, error){
        let citeModal = $('#citeproc-modal');
        let contentArea = $(citeModal).find('#citeproc-modal-inner');

        if( error ){
          contentArea.html('<p><em>' + error + '</em></p>');
          return
        }

        let html = '<div class="accordion" id="citeproc-accordion">';
        for( let i = 0; i < data.length; i++ ){
          html += build_cite_section(i, data[i]);
        }
        html += '</div';

        contentArea.html(html);

        if( navigator.clipboard ){
          let sections = $(contentArea).find('.accordion-item');
          $(sections).each(function(_index, _section){
            let citationEl = $(_section).find('pre');
            let citationHTML = $(citationEl).html();
            citationHTML = new Blob([citationHTML], {type: 'text/html'});
            let citationPlainText = $(citationEl).text();
            citationPlainText = new Blob([citationPlainText], {type: 'text/plain'});
            let clipData = [new ClipboardItem({
                ['text/plain']: citationPlainText,
                ['text/html']: citationHTML,
            })];
            let button = $(_section).find('.accordion-body').find('button');
            $(button).off('click.Copy');
            $(button).on('click.Copy', function(_event){
              navigator.clipboard.write(clipData).then(function(){
                $(button).removeClass('btn-secondary').addClass('btn-success');
                setTimeout(function(){
                  $(button).removeClass('btn-success').addClass('btn-secondary');
                }, 3600);
              });
            });
          });
        }
      }

      $.ajax({
        'url': this.options.ajax_uri,
        'type': 'GET',
        'complete': function(_data){
          if( _data.responseJSON ){  // we have response JSON
            if( _data.responseJSON.success ){  // successful format guess
              build_content(_data.responseJSON.result, null);
            }else{  // validation error
              build_content(null, _('Failed to get citations'));
            }
          }else{  // fully flopped ajax request
            build_content(null, _('Failed to get citations'));
          }
        }
      });
    }
  };
});
