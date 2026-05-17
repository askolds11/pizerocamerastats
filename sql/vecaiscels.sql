SELECT EXTRACT(EPOCH FROM (cp."PictureRequestReceived" - pr."RequestTime")) * 1000 AS "DifferenceMs"
FROM "CameraPictures" cp
JOIN "PictureRequests" pr ON cp."PictureRequestId" = pr."Uuid"
WHERE cp."CameraPictureStatus" IS NOT NULL
  AND cp."PictureRequestReceived" IS NOT NULL
  AND cp."CameraPictureStatus" <> 'Cancelled'
  AND pr."PictureTime" <= TIMESTAMPTZ '2026-03-02 11:25:56.646204 +00:00'
ORDER BY "DifferenceMs" DESC;