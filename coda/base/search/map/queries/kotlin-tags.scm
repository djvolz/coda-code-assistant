;; Kotlin tag queries for code intelligence
;; This file defines tree-sitter queries for extracting semantic information from Kotlin code.
;; Supports classes, objects, functions, properties, and imports.
;; Based on tree-sitter-kotlin grammar structure.

;; Class declarations
;; Captures regular classes, data classes, and sealed classes
(class_declaration
  (type_identifier) @name.definition.class) @definition.class

;; Object declarations
;; Captures Kotlin object declarations (singletons) and companion objects
(object_declaration
  "object" (type_identifier) @name.definition.class) @definition.class

;; Function declarations
;; Captures top-level and member functions, including extension functions
(function_declaration
  (simple_identifier) @name.definition.function) @definition.function

;; Property declarations
;; Captures property declarations with val/var keywords
(property_declaration
  (variable_declaration
    (simple_identifier) @name.definition.variable)) @definition.variable

;; Import statements
;; Captures import directives for dependency tracking
(import_header
  (identifier) @name.import) @import

;; Package declaration
;; Captures the package declaration at the top of Kotlin files
(package_header
  (identifier) @name.definition.module) @definition.module

;; Function calls
;; Captures function invocations for reference tracking
(call_expression
  (simple_identifier) @name.reference.call) @reference.call

;; Type references
;; Captures type usage in declarations and expressions
(user_type
  (type_identifier) @name.reference.class) @reference.class