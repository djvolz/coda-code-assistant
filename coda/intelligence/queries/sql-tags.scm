;; SQL tag queries for code intelligence
;; Supports standard SQL and some PL/SQL constructs

;; Create table statements
(create_table
  (object_reference
    name: (identifier) @name.definition.class)) @definition.class

;; Create view statements  
(create_view
  (object_reference
    name: (identifier) @name.definition.class)) @definition.class

;; Create function statements
(create_function
  (object_reference
    name: (identifier) @name.definition.function)) @definition.function

;; Create procedure statements
(create_procedure
  (object_reference
    name: (identifier) @name.definition.function)) @definition.function

;; Create trigger statements
(create_trigger
  (object_reference
    name: (identifier) @name.definition.function)) @definition.function

;; Create index statements
(create_index
  name: (object_reference
    name: (identifier) @name.definition.variable)) @definition.variable

;; Table references in FROM clause
(from_clause
  (from_item
    (from_table
      (object_reference
        name: (identifier) @name.reference.class)))) @reference.class

;; Column references
(column
  name: (identifier) @name.reference.property) @reference.property

;; Function calls
(invocation
  name: (object_reference
    name: (identifier) @name.reference.call)) @reference.call