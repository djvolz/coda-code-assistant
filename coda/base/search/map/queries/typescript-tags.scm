;; TypeScript tag queries for code intelligence
;; Extends JavaScript patterns with TypeScript-specific constructs

;; Include all JavaScript patterns
;; (Note: In practice, we'd use the JavaScript queries as a base)

;; Interfaces
(interface_declaration
  name: (type_identifier) @name.definition.interface) @definition.interface

;; Type aliases
(type_alias_declaration
  name: (type_identifier) @name.definition.type) @definition.type

;; Enums
(enum_declaration
  name: (identifier) @name.definition.enum) @definition.enum

;; Class declarations (including abstract)
(class_declaration
  name: (type_identifier) @name.definition.class) @definition.class

;; Function declarations
(function_declaration
  name: (identifier) @name.definition.function) @definition.function

;; Methods
(method_definition
  name: (property_identifier) @name.definition.method) @definition.method

;; Constructor
(method_definition
  name: (property_identifier) @name.definition.constructor
  (#eq? @name.definition.constructor "constructor")) @definition.constructor

;; Properties
(public_field_definition
  name: (property_identifier) @name.definition.property) @definition.property

;; Function expressions and arrow functions
(variable_declarator
  name: (identifier) @name.definition.function
  value: [
    (function_expression)
    (arrow_function)
  ]) @definition.function

;; Variable declarations
(variable_declarator
  name: (identifier) @name.definition.variable) @definition.variable

;; Const declarations
(lexical_declaration
  kind: "const"
  (variable_declarator
    name: (identifier) @name.definition.constant)) @definition.constant

;; Import statements
(import_statement
  (import_clause
    (identifier) @name.import)) @import

(import_statement
  (import_clause
    (named_imports
      (import_specifier
        name: (identifier) @name.import)))) @import

;; Export statements
(export_statement
  declaration: [
    (function_declaration
      name: (identifier) @name.definition.function)
    (class_declaration
      name: (type_identifier) @name.definition.class)
    (interface_declaration
      name: (type_identifier) @name.definition.interface)
    (type_alias_declaration
      name: (type_identifier) @name.definition.type)
    (enum_declaration
      name: (identifier) @name.definition.enum)
  ])

;; Function calls
(call_expression
  function: (identifier) @name.reference.call) @reference.call

;; Type references
(type_identifier) @name.reference.type

;; Class instantiation
(new_expression
  constructor: (identifier) @name.reference.class) @reference.class