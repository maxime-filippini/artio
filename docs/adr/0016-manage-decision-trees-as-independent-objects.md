# Manage decision trees as independent objects

Decision trees are independently named and browsable Expression assets with their own draft and explicit-save lifecycle, rather than transient edits to a Transformation body. They are reusable from multiple Transformations, with each use choosing its output-column alias and explicitly binding every Tree parameter to either a column or literal; parameters have no defaults. Artio updates code and permits Preview only after a Decision tree is valid and saved, so authors can build complex rule sets without repeatedly executing incomplete work.
