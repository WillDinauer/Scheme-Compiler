(let ((a 4) (b 3))                ; One type of comment
    (+ a (* b (let ((a 5)) a)))) #| Comment type #2 |#


(* (if #t (- 5 2) (* 3 2)) (let ((hm (+ 53 122)) (ya (* 60 20))) (+ hm ya)))