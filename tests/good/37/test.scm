(let ((plus (lambda (x y) (+ x y))))
    (foldr plus 0 (cons 1 (cons 2 (cons 3 '())))))