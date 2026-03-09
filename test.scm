(let ((fact
          (lambda (n)
            (letrec ((fact-iter
                      (lambda (n acc)
                        (if (= n 0)
                            acc
                            (fact-iter (- n 1) (* acc n))))))
              (fact-iter n 1)))))
  (fact 6))