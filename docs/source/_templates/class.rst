{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :exclude-members: __init__, __new__

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

   {%- if attributes %}
   .. rubric:: {{ _('Attributes') }}

   {%- for item in attributes %}
   .. autoattribute:: {{ name }}.{{ item }}
   {%- endfor %}
   {%- endif %}

   {%- if methods %}
   .. rubric:: {{ _('Methods') }}

   {%- for item in methods %}
   {%- if item != "__init__" %}
   .. automethod:: {{ name }}.{{ item }}
   {%- endif %}
   {%- endfor %}
   {%- if module == "argclz.validator" and "Validator" in name %}
   .. automethod:: {{ name }}.__call__
   {%- endif %}
   {%- endif %}
