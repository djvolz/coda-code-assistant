;; Python tag queries for code intelligence
;; This file defines tree-sitter queries for extracting semantic information from Python code.
;; It identifies classes, functions, methods, imports, and other code elements.
;; Based on aider's implementation with enhancements for better Python support.

;; Classes
;; Captures class definitions with their names for code navigation and analysis
(class_definition
  name: (identifier) @name.definition.class) @definition.class

;; Functions
;; Captures top-level function definitions (not methods inside classes)
(function_definition
  name: (identifier) @name.definition.function) @definition.function

;; Methods (functions inside classes)
;; Captures methods defined within class bodies, including special methods like __init__
(class_definition
  body: (block
    (function_definition
      name: (identifier) @name.definition.method))) @definition.method

;; Decorated methods inside classes
;; Captures methods that have decorators (e.g., @property, @staticmethod)
(class_definition
  body: (block
    (decorated_definition
      (function_definition
        name: (identifier) @name.definition.method)))) @definition.method

;; Decorated definitions
;; Captures functions and classes that have decorators applied at the module level
(decorated_definition
  (decorator) @decorator
  (function_definition
    name: (identifier) @name.definition.function)) @definition.function

(decorated_definition
  (decorator) @decorator
  (class_definition
    name: (identifier) @name.definition.class)) @definition.class

;; Assignments (module-level variables/constants)
;; Captures variable assignments at module level, used for constants and configuration
(module
  (expression_statement
    (assignment
      left: (identifier) @name.definition.variable))) @definition.variable

;; Type aliases
;; Captures type alias definitions using typing module (e.g., MyType = List[str])
(module
  (expression_statement
    (assignment
      left: (identifier) @name.definition.type
      right: (subscript
        value: (attribute
          object: (identifier) @typing (#eq? @typing "typing")))))) @definition.type

;; Imports
;; Captures import statements including 'import X', 'from X import Y', and aliased imports
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
;; Captures function and method invocations for dependency tracking
(call
  function: [
    (identifier) @name.reference.call
    (attribute
      attribute: (identifier) @name.reference.call)
  ]) @reference.call

;; Class instantiation
;; Captures class constructor calls (e.g., MyClass())
(call
  function: (identifier) @name.reference.class) @reference.class

;; Attribute access
;; Captures attribute access patterns (e.g., obj.attribute)
(attribute
  object: (identifier) @name.reference.variable
  attribute: (identifier) @name.reference.attribute) @reference.attribute

;; Documentation strings
;; Captures docstrings at module, class, and function levels for documentation extraction
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