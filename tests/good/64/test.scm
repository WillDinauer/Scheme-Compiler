(let* ((plus (lambda (x y) (+ x y))) (var-plus (lambda (a . b) (foldl plus a b))))
    (apply var-plus (list 10 20 30 40 50))
)