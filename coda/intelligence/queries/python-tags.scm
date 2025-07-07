;; Python tag queries for code intelligence
;; Based on aider's approach but simplified for our use case

;; Classes
(class_definition
  name: (identifier) @name.definition.class) @definition.class

;; Functions
(function_definition
  name: (identifier) @name.definition.function) @definition.function

;; Methods (functions inside classes)
(class_definition
  body: (block
    (function_definition
      name: (identifier) @name.definition.method))) @definition.method

;; Decorated definitions
(decorated_definition
  (decorator) @decorator
  (function_definition
    name: (identifier) @name.definition.function)) @definition.function

(decorated_definition
  (decorator) @decorator
  (class_definition
    name: (identifier) @name.definition.class)) @definition.class

;; Assignments (module-level variables/constants)
(module
  (expression_statement
    (assignment
      left: (identifier) @name.definition.variable))) @definition.variable

;; Type aliases
(module
  (expression_statement
    (assignment
      left: (identifier) @name.definition.type
      right: (subscript
        value: (attribute
          object: (identifier) @typing (#eq? @typing "typing")))))) @definition.type

;; Imports
(import_statement
  name: (dotted_name) @name.import) @import

(import_from_statement
  module_name: (dotted_name) @name.import
  name: (dotted_name) @name.import) @import

(import_from_statement
  module_name: (dotted_name) @name.import
  (aliased_import
    name: (dotted_name) @name.import)) @import

;; Function calls (references)
(call
  function: [
    (identifier) @name.reference.call
    (attribute
      attribute: (identifier) @name.reference.call)
  ]) @reference.call

;; Class instantiation
(call
  function: (identifier) @name.reference.class) @reference.class

;; Attribute access
(attribute
  object: (identifier) @name.reference.variable
  attribute: (identifier) @name.reference.attribute) @reference.attribute

;; Documentation strings
(module
  . (expression_statement
    (string) @module.docstring))

(class_definition
  name: (identifier)
  body: (block
    . (expression_statement
      (string) @class.docstring)))

(function_definition
  name: (identifier)
  body: (block
    . (expression_statement
      (string) @function.docstring)))