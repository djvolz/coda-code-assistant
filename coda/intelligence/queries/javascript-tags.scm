;; JavaScript tag queries for code intelligence
;; This file defines tree-sitter queries for extracting semantic information from JavaScript code.
;; Supports ES6+ syntax, CommonJS, classes, functions, imports/exports, and JSDoc.
;; Based on aider's implementation with enhancements for modern JavaScript.

;; Class declarations
;; Captures ES6 class definitions (e.g., class MyClass {})
(class_declaration
  name: (_) @name.definition.class) @definition.class

;; Function declarations
;; Captures traditional function declarations (e.g., function myFunc() {})
(function_declaration
  name: (identifier) @name.definition.function) @definition.function

;; Function expressions and arrow functions
;; Captures functions assigned to variables (e.g., const fn = () => {})
(variable_declarator
  name: (identifier) @name.definition.function
  value: [
    (function_expression)
    (arrow_function)
  ]) @definition.function

;; Generator functions
;; Captures generator function declarations (e.g., function* myGen() {})
(generator_function_declaration
  name: (identifier) @name.definition.function) @definition.function

;; Methods with documentation
;; Captures class methods with preceding JSDoc comments, excluding constructors
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
;; Specifically captures class constructor methods
(method_definition
  name: (property_identifier) @name.definition.constructor
  (#eq? @name.definition.constructor "constructor")) @definition.constructor

;; Object properties that are functions
;; Captures methods defined in object literals (e.g., { myMethod: function() {} })
(pair
  key: (property_identifier) @name.definition.method
  value: [
    (function_expression)
    (arrow_function)
  ]) @definition.method

;; Variable declarations (excluding functions)
;; Captures let, const, and var declarations that aren't function assignments
(variable_declarator
  name: (identifier) @name.definition.variable
  value: (_) @value
  (#not-match? @value "^(function_expression|arrow_function)$")) @definition.variable

;; Const declarations
;; Specifically captures const variable declarations
(lexical_declaration
  kind: "const"
  (variable_declarator
    name: (identifier) @name.definition.constant)) @definition.constant

;; Import statements
;; Captures ES6 import sources (e.g., import X from 'module-name')
(import_statement
  source: (string (string_fragment) @name.import)) @import

;; Named imports
;; Captures named imports as variable definitions (e.g., import { foo, bar } from 'module')
(import_statement
  (import_clause
    (named_imports
      (import_specifier
        name: (identifier) @name.definition.variable)))) @definition.variable

;; Default imports
;; Captures default imports as variable definitions (e.g., import React from 'react')
(import_statement
  (import_clause
    (identifier) @name.definition.variable)) @definition.variable

;; Namespace imports
;; Captures namespace imports (e.g., import * as utils from './utils')
(import_statement
  (import_clause
    (namespace_import
      (identifier) @name.definition.variable))) @definition.variable

;; Require statements (CommonJS)
;; Captures CommonJS require() calls and extracts module paths
(variable_declarator
  name: (identifier) @name.definition.variable
  value: (call_expression
    function: (identifier) @require
    (#eq? @require "require")
    arguments: (arguments
      (string (string_fragment) @name.import)))) @import

;; Export statements
;; Captures exported functions, classes, and variables
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
;; Captures function and method invocations for dependency tracking
(call_expression
  function: (identifier) @name.reference.call) @reference.call

(call_expression
  function: (member_expression
    property: (property_identifier) @name.reference.call)) @reference.call

;; New expressions (class instantiation)
;; Captures class constructor calls (e.g., new MyClass())
(new_expression
  constructor: (_) @name.reference.class) @reference.class

;; Member access
;; Captures property access on objects (e.g., obj.property)
(member_expression
  object: (identifier) @name.reference.variable
  property: (property_identifier) @name.reference.property) @reference.property

;; JSDoc comments
;; Captures JSDoc-style documentation comments (/** ... */) associated with definitions
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