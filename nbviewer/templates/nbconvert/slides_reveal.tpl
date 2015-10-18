{%- extends 'basic.tpl' -%}

{%- block any_cell scoped -%}
{%- if cell.metadata.slide_type in ['slide'] -%}
    <section>
    <section>
    {{ super() }}
{%- elif cell.metadata.slide_type in ['subslide'] -%}
    <section>
    {{ super() }}
{%- elif cell.metadata.slide_type in ['-'] -%}
    {%- if cell.metadata.frag_helper in ['fragment_end'] -%}
        <div class="fragment" data-fragment-index="{{ cell.metadata.frag_number }}">
        {{ super() }}
        </div>
    {%- else -%}
        {{ super() }}
    {%- endif -%}
{%- elif cell.metadata.slide_type in ['skip'] -%}
    <div style=display:none>
    {{ super() }}
    </div>
{%- elif cell.metadata.slide_type in ['notes'] -%}
    <aside class="notes">
    {{ super() }}
    </aside>
{%- elif cell.metadata.slide_type in ['fragment'] -%}
    <div class="fragment" data-fragment-index="{{ cell.metadata.frag_number }}">
    {{ super() }}
    </div>
{%- endif -%}
{%- if cell.metadata.slide_helper in ['subslide_end'] -%}
    </section>
{%- elif cell.metadata.slide_helper in ['slide_end'] -%}
    </section>
    </section>
{%- endif -%}
{%- endblock any_cell -%}

{% block body %}
<div class="reveal">
<div class="slides">
{{ super() }}
</div>
</div>
{% endblock body %}
