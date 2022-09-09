unit PolyOvl;

interface

uses
  Windows, SysUtils, Math;


type
  TPointArray = array of TPoint;

function IsPointInPolygon(P: TPoint; Pg: TPointArray): boolean;
function IsPolygonOverlap(Poly1, Poly2: TPointArray): boolean;


implementation

var
  RandomPoint: TPoint;

//http://www.delphipages.com/tips/thread.cfm?ID=236
function SegmentsIntersect(P1,P2,Q1,Q2: TPoint): boolean;
var
  UpperX,UpperY : Double;
  LowerX,LowerY : Double;
  Ax,Bx,Cx      : Double;
  Ay,By,Cy      : Double;
  D,F,E         : Double;
begin
  Result := false;

  Ax := P2.x - P1.x; 
  Bx := Q1.x - Q2.x; 

  if Ax < 0
    then begin LowerX := P2.x; UpperX := P1.x; end
    else begin UpperX := P2.x; LowerX := P1.x; end;

  if Bx > 0
    then begin if (UpperX < Q2.x) or (Q1.x < LowerX) then Exit; end
    else begin if (Upperx < Q1.x) or (Q2.x < LowerX) then Exit; end;



  Ay := P2.y - P1.y;
  By := Q1.y - Q2.y;

  if Ay < 0
    then begin LowerY := P2.y; UpperY := P1.y; end
    else begin UpperY := P2.y; LowerY := P1.y; end;

  if By > 0
    then begin if (UpperY < Q2.y) or (Q1.y < LowerY) then Exit; end
    else begin if (UpperY < Q1.y) or (Q2.y < LowerY) then Exit; end;




  Cx := P1.x - Q1.x;
  Cy := P1.y - Q1.y;
  d  := (By * Cx) - (Bx * Cy);
  f  := (Ay * Bx) - (Ax * By);

  if f > 0
    then begin if (d < 0) or (d > f) then Exit; end
    else begin if (d > 0) or  (d < f) then Exit; end;




  e := (Ax * Cy) - (Ay * Cx);

  if f > 0
    then begin if (e < 0) or (e > f) then Exit; end
    else begin if(e > 0) or (e < f) then Exit; end;

  Result := true;
end;


function IsPointInPolygon(P: TPoint; Pg: TPointArray): boolean;
var
  i, Cnt: integer;
begin
  Cnt := 0;
  
  for i:=0 to High(Pg)-1 do
    if SegmentsIntersect(P, RandomPoint, Pg[i], Pg[i+1])
      then Inc(Cnt);

  Result := Odd(Cnt);
end;


function IsPolygonOverlap(Poly1, Poly2: TPointArray): boolean;
var
  i, j: integer;
begin
  Result := IsPointInPolygon(Poly1[0], Poly2) or
            IsPointInPolygon(Poly2[0], Poly1);
  if Result then Exit;

  for i:=0 to High(Poly1)-1 do
    begin
    for j:=0 to High(Poly2)-1 do
      begin
      Result := Result or SegmentsIntersect(Poly1[i], Poly1[i+1], Poly2[j], Poly2[j+1]);
      if Result then Exit;
      end;
    end;
end;



initialization
  RandomPoint.x := Random(MAXINT);
  RandomPoint.y := Random(MAXINT);

  
end.

