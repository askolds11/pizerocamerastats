SELECT
    cp."CameraId",
    AVG(cp."NtpErrorMillis") AS "AvgNtpErrorMillis"
FROM "CameraPictures" cp
         JOIN "PictureRequests" pr ON pr."Uuid" = cp."PictureRequestId"
WHERE cp."NtpErrorMillis" IS NOT NULL
  AND pr."PictureSetId" IS NOT NULL
  AND pr."PictureTime" <= TIMESTAMPTZ '2026-03-02 11:25:56.646204 +00:00'
GROUP BY
    pr."PictureSetId",
    cp."CameraId"
UNION
SELECT
    cp."CameraId",
    cp."NtpErrorMillis" AS "AvgNtpErrorMillis"
FROM "CameraPictures" cp
         JOIN "PictureRequests" pr ON pr."Uuid" = cp."PictureRequestId"
WHERE cp."NtpErrorMillis" IS NOT NULL AND pr."PictureSetId" IS NULL AND pr."PictureTime" <= TIMESTAMPTZ '2026-03-02 11:25:56.646204 +00:00'