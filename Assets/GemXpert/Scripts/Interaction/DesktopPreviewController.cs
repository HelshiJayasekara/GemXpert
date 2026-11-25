using System;
using UnityEngine;
using UnityEngine.InputSystem;

namespace GemXpert.Interaction
{
    /// <summary>
    /// Mouse + keyboard control of the XR rig when no headset (and no simulator) is in use.
    /// Comfort-first: no acceleration, no head bob, slow walking speed, pitch clamped, and the
    /// rig cannot leave the showroom floor bounds.
    ///   Right mouse drag : look        W A S D / arrows : walk
    ///   M                : recall menu  R                : reset view
    /// UI clicks are handled by the EventSystem (XRUIInputModule mouse support), not here.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class DesktopPreviewController : MonoBehaviour
    {
        [SerializeField] private Transform rigRoot;
        [SerializeField] private Camera viewCamera;
        [SerializeField] private float eyeHeight = 1.6f;
        [SerializeField] private float walkSpeed = 1.3f;
        [SerializeField] private float lookDegreesPerPixel = 0.12f;
        [SerializeField] private float maxPitch = 70f;
        [Tooltip("Walkable area on the XZ plane (world metres): x/y = min corner, width/height = size.")]
        [SerializeField] private Rect floorBounds = new Rect(-5.4f, -3.4f, 10.8f, 8.8f);

        public event Action RecallMenuRequested;

        private float _pitch;
        private Vector3 _startPosition;
        private Quaternion _startRotation;
        private bool _captured;

        public Camera ViewCamera => viewCamera;

        public void Configure(Transform rig, Camera cam)
        {
            rigRoot = rig;
            viewCamera = cam;
        }

        private void Awake()
        {
            if (rigRoot == null) rigRoot = transform;
            if (viewCamera == null) viewCamera = Camera.main;
            _startPosition = rigRoot.position;
            _startRotation = rigRoot.rotation;
        }

        private void OnEnable()
        {
            if (viewCamera == null) viewCamera = Camera.main;
            PlaceCameraAtEyeHeight();
        }

        private void PlaceCameraAtEyeHeight()
        {
            if (viewCamera == null || rigRoot == null) return;
            var cam = viewCamera.transform;
            cam.position = new Vector3(rigRoot.position.x, rigRoot.position.y + eyeHeight, rigRoot.position.z);
            cam.rotation = rigRoot.rotation;
            _pitch = 0f;
        }

        private void Update()
        {
            var mouse = Mouse.current;
            var keyboard = Keyboard.current;
            if (mouse == null || keyboard == null || viewCamera == null) return;

            // Look
            if (mouse.rightButton.isPressed)
            {
                var delta = mouse.delta.ReadValue() * lookDegreesPerPixel;
                rigRoot.Rotate(0f, delta.x, 0f, Space.World);
                _pitch = Mathf.Clamp(_pitch - delta.y, -maxPitch, maxPitch);
                viewCamera.transform.rotation = rigRoot.rotation * Quaternion.Euler(_pitch, 0f, 0f);
            }

            // Walk (relative to where the camera faces, flattened to the floor)
            var input = Vector2.zero;
            if (keyboard.wKey.isPressed || keyboard.upArrowKey.isPressed) input.y += 1f;
            if (keyboard.sKey.isPressed || keyboard.downArrowKey.isPressed) input.y -= 1f;
            if (keyboard.dKey.isPressed || keyboard.rightArrowKey.isPressed) input.x += 1f;
            if (keyboard.aKey.isPressed || keyboard.leftArrowKey.isPressed) input.x -= 1f;
            if (input.sqrMagnitude > 0f)
            {
                var forward = Vector3.ProjectOnPlane(viewCamera.transform.forward, Vector3.up).normalized;
                var right = Vector3.ProjectOnPlane(viewCamera.transform.right, Vector3.up).normalized;
                var move = (forward * input.y + right * input.x).normalized * (walkSpeed * Time.deltaTime);
                var before = rigRoot.position;
                var next = before + move;
                next.x = Mathf.Clamp(next.x, floorBounds.xMin, floorBounds.xMax);
                next.z = Mathf.Clamp(next.z, floorBounds.yMin, floorBounds.yMax);
                MoveRig(next - before);
                // The camera may not be a child of rigRoot in every rig layout; keep it with the rig.
                if (!viewCamera.transform.IsChildOf(rigRoot)) viewCamera.transform.position += rigRoot.position - before;
            }

            if (keyboard.mKey.wasPressedThisFrame) RecallMenuRequested?.Invoke();
            if (keyboard.rKey.wasPressedThisFrame) ResetView();
        }

        private void LateUpdate()
        {
            // XROrigin may (re)apply its camera-offset height while it waits for an XR input subsystem
            // that never arrives in Desktop mode. Keep the eye at a fixed standing height.
            if (viewCamera == null || rigRoot == null) return;
            var cam = viewCamera.transform;
            var p = cam.position;
            var wantY = rigRoot.position.y + eyeHeight;
            if (Mathf.Abs(p.y - wantY) > 0.001f) cam.position = new Vector3(p.x, wantY, p.z);
        }

        public void ResetView()
        {
            // A CharacterController keeps its own position; disable it while teleporting the rig.
            var cc = rigRoot.GetComponent<CharacterController>();
            var ccWasEnabled = cc != null && cc.enabled;
            if (ccWasEnabled) cc.enabled = false;
            rigRoot.SetPositionAndRotation(_startPosition, _startRotation);
            if (ccWasEnabled) cc.enabled = true;
            PlaceCameraAtEyeHeight();
            RecallMenuRequested?.Invoke();
        }

        /// <summary>
        /// Moves through the rig's CharacterController when it has one (the XRI Starter rig does),
        /// so walls block movement and the controller does not snap the rig back to its old position.
        /// </summary>
        private void MoveRig(Vector3 delta)
        {
            var cc = rigRoot.GetComponent<CharacterController>();
            if (cc != null && cc.enabled)
            {
                cc.Move(delta);
            }
            else
            {
                rigRoot.position += delta;
            }
        }
    }
}
