-- select the first vehicle rec you can find and set all trips as belogning to the user
BEGIN;
update trip set user_id = (select user_id from vehicle limit 1);
COMMIT;