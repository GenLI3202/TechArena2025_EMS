\* Source Pyomo model name=unknown *\

max 
x1:
+1 x2
+1 x3

s.t.

c_u_x4_:
+1 x2
+2 x3
<= 15

bounds
   0 <= x2 <= 10
   0 <= x3 <= 10
end
