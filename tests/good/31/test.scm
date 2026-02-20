(letrec ((a (lambda (x) (if (= x 0) 0 (+ x (a (- x 1)))))))
    (a 5))