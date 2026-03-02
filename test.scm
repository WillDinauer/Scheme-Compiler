(let ((a (cons 1 (cons 2 '()))) (b (lambda (x) (+ x 1))))
    (car (cdr (map b a)))
)