;; JavaScript tag queries for code intelligence
;; Based on aider's approach but simplified for our use case

;; Class declarations
(class_declaration
  name: (_) @name.definition.class) @definition.class

;; Function declarations
(function_declaration
  name: (identifier) @name.definition.function) @definition.function

;; Function expressions and arrow functions
(variable_declarator
  name: (identifier) @name.definition.function
  value: [
    (function_expression)
    (arrow_function)
  ]) @definition.function

;; Generator functions
(generator_function_declaration
  name: (identifier) @name.definition.function) @definition.function

;; Methods with documentation
(
  (comment)* @doc
  .
  (method_definition
    name: (property_identifier) @name.definition.method) @definition.method
  (#not-eq? @name.definition.method "constructor")
  (#strip! @doc "^[\\s\\*/]+|^[\\s\\*/]$")
  (#select-adjacent! @doc @definition.method)
)

;; Constructor
(method_definition
  name: (property_identifier) @name.definition.constructor
  (#eq? @name.definition.constructor "constructor")) @definition.constructor

;; Object properties that are functions
(pair
  key: (property_identifier) @name.definition.method
  value: [
    (function_expression)
    (arrow_function)
  ]) @definition.method

;; Variable declarations (excluding functions)
(variable_declarator
  name: (identifier) @name.definition.variable
  value: (_) @value
  (#not-match? @value "^(function_expression|arrow_function)$")) @definition.variable

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
      name: (identifier) @name.definition.class)
    (lexical_declaration
      (variable_declarator
        name: (identifier) @name.definition.variable))
  ]) @definition.export

;; Function calls
(call_expression
  function: (identifier) @name.reference.call) @reference.call

(call_expression
  function: (member_expression
    property: (property_identifier) @name.reference.call)) @reference.call

;; New expressions (class instantiation)
(new_expression
  constructor: (_) @name.reference.class) @reference.class

;; Member access
(member_expression
  object: (identifier) @name.reference.variable
  property: (property_identifier) @name.reference.property) @reference.property

;; JSDoc comments
(
  (comment) @doc
  .
  [
    (function_declaration)
    (class_declaration)
    (method_definition)
    (variable_declarator)
  ] @documented
  (#match? @doc "^/\\*\\*")
  (#strip! @doc "^/\\*\\*|\\*/$|^\\s*\\*\\s?")
)