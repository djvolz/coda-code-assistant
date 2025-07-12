;; PHP tag queries for code intelligence
;; Simple patterns to start with

;; Class declarations
(class_declaration
  name: (name) @name.definition.class) @definition.class

;; Interface declarations  
(interface_declaration
  name: (name) @name.definition.interface) @definition.interface

;; Function declarations
(function_definition
  name: (name) @name.definition.function) @definition.function

;; Method declarations
(method_declaration
  name: (name) @name.definition.method) @definition.method

;; Namespace declarations
(namespace_definition
  name: (namespace_name) @name.definition.module) @definition.module

;; Use statements (imports)
(namespace_use_declaration
  (namespace_use_clause
    (qualified_name) @name.import)) @import

;; Function calls
(function_call_expression
  function: (name) @name.reference.call) @reference.call

;; Variable assignments
(assignment_expression
  left: (variable_name) @name.definition.variable) @definition.variable