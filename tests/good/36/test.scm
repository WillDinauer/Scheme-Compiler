(let ((a (cons 1 (cons 2 (cons 3 '())))) (b (lambda (x) (+ x 4))))
    (car (cdr (map b a)))
)