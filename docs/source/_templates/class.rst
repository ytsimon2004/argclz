{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :members:
   :undoc-members:
   :exclude-members: __init__, __new__
   {% if module == "argclz.validator" and "Validator" in name -%}
   :special-members: __call__
   {%- endif %}

   {% block methods %}
   .. automethod:: __init__

   {% if methods %}
   .. rubric:: {{ _('Methods Summary') }}

   .. autosummary::
   {%- for item in methods %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {%- endif %}
   {% endblock %}

   {% block attributes %}
   {%- if attributes %}
   .. rubric:: {{ _('Attributes Summary') }}

   .. autosummary::
   {%- for item in attributes %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {%- endif %}
   {% endblock %}

   .. rubric:: {{ _('Details') }}


