{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :members:
   :undoc-members:
   :exclude-members: __init__, __new__, count, index
   {% if module == "argclz.validator" and name == "AbstractTypeValidatorBuilder" -%}
   :special-members: __and__, __or__
   {%- elif module == "argclz.validator" and "Validator" in name -%}
   :special-members: __call__
   {%- endif %}
   {%- if module == "argclz.dispatch.core" and name == "DispatchCommand" -%}
   :special-members: __call__
   {%- endif %}
   {%- if module == "argclz.dispatch.core" and name == "DispatchGroup" -%}
   :special-members: __call__, __get__
   {%- endif %}

   {% block methods %}
   .. automethod:: __init__

   {% if methods %}
   .. rubric:: {{ _('Methods Summary') }}

   .. autosummary::
   {%- for item in methods %}
   {%- if item not in ['index', 'count'] %}
      ~{{ name }}.{{ item }}
   {%- endif %}
   {%- endfor %}
   {%- endif %}
   {%- if module == "argclz.validator" and name == "AbstractTypeValidatorBuilder" %}
      ~{{ name }}.__call__
      ~{{ name }}.__and__
      ~{{ name }}.__or__
   {%- elif module == "argclz.validator" and "Validator" in name %}
      ~{{ name }}.__call__
   {%- endif %}
   {%- if module == "argclz.dispatch.core" and name == "DispatchCommand" %}
      ~{{ name }}.__call__
   {%- endif %}
   {%- if module == "argclz.dispatch.core" and name == "DispatchGroup" %}
      ~{{ name }}.__call__
      ~{{ name }}.__get__
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


