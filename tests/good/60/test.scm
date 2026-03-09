(letrec ((is-odd? (lambda (x) (if (= x 0) #f (is-even? (- x 1))))) (is-even? (lambda (x) (if (= x 0) #t (is-odd? (- x 1))))))
    (is-odd? 98))