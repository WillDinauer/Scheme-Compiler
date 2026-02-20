(letrec ((a 
          (lambda (x) (
            if (= x 0) 
              0 
              (let ((c (lambda (d) (+ (a (- x 1)) d)))) 
                 (* (c 2) (c 3)))))))
    (a 2))  ; (a 1) is 6. So this is like doing (6 + 2) * (6 + 3) = 72