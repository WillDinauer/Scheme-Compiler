(letrec ((a (lambda (x) x)) (b (lambda (y) (+ 1 y))))
    (if #f
        (a 3)
        (b 3)
    ))