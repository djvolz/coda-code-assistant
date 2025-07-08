;; R language tag queries for code intelligence
;; Captures function definitions and function calls

;; Function definitions using <- operator
(binary_operator
    lhs: (identifier) @name.definition.function
    operator: "<-"
    rhs: (function_definition)
) @definition.function

;; Function definitions using = operator
(binary_operator
    lhs: (identifier) @name.definition.function
    operator: "="
    rhs: (function_definition)
) @definition.function

;; Function calls
(call
    function: (identifier) @name.reference.call
) @reference.call

;; Namespaced function calls (e.g., package::function)
(call
    function: (namespace_operator
        rhs: (identifier) @name.reference.call
    )
) @reference.call