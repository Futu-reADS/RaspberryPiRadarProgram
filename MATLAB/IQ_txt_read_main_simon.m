addpath(genpath(pwd))
clc
clear all
format shorteng

%filename = 'Ton10_Sweep100_0227_Test3.csv'
filename = 'Manniska_Sweep100_Test3.csv' %Used most often
%filename = 'Ton20_Sweep100_0227_Test2.csv'

[dist,amp, phase,t,S,D,A,P, gain, L_start, L_end, L_data, L_seq, Fs] = IQ_read_3_test(filename);
gain = gain
L_start = L_start
L_end = L_end
L_data = L_data
L_seq = L_seq
Fs = Fs
c = 3e8;%[m/s] 
fc = 60.5e9;% [Hz]
wavelength = c/fc

%Detektering och f�ljning utav m�l
start_distance = 0.37%m
N_avg = 10;
[t,target_amplitude, target_phase, target_distance] = target_tracker_2(t,dist,amp,phase,start_distance,N_avg);

%target_amplitude_PCA = amp(:,1);
%target_phase_PCA = phase(:,1);
%target_amplitude = target_amplitude_PCA;
%target_phase = target_phase_PCA;

figure(12)
imagesc(amp)
title('PCA-amplitud')
xlabel('distans')
ylabel('sekvens (tid)')
colorbar

figure(1)
subplot(1,2,1)
%plot(dist,amp(1,:))
plot(dist,amp(200,:))
ylabel('Amplitude []')
xlabel('Distance [m]')


subplot(1,2,2)
plot(dist,phase(1,:))
ylabel('phase []')
xlabel('Distance [m]')

% 

%unwrap test
target_phase = unwrap(target_phase);

figure(7)
%I = target_amplitude(1:L_seq/2).*cos(target_phase(1:L_seq/2));
%Q = target_amplitude(1:L_seq/2).*sin(target_phase(1:L_seq/2));

I = target_amplitude(L_seq/4:L_seq/2).*cos(target_phase(L_seq/4:L_seq/2));
Q = target_amplitude(L_seq/4:L_seq/2).*sin(target_phase(L_seq/4:L_seq/2));
plot(I,Q)



%Signal filtreringstest
disp('Downsampling with ratio r:')
r = 1
%Down sampling
target_amplitude = decimate(target_amplitude,r);
target_phase = decimate(target_phase,r);
target_distance = decimate(target_distance,r);
t = decimate(t,r);
L_seq = L_seq/r%new length in time domain
Fs = Fs/r%New sample rate in time domain


%Delta distance of tracked target
target_delta_distance = wavelength/2/pi/2*target_phase;

%Windowing
W = window(@flattopwin,1,L_seq)';
target_amplitude = target_amplitude .* W;
target_phase = target_phase .* W;
target_distance = target_distance .* W;

%Padded FFT
FFT_resolution = 0.001%[Hz resolution]
L_fft = max(Fs/FFT_resolution,L_seq)%needed length of FFT, or orignial.
f = Fs*(0:(L_fft/2))/L_fft;

Y = fft(target_delta_distance - mean(target_delta_distance),L_fft);
P2 = abs(Y/L_fft);
P1 = P2(1:L_fft/2+1);
P1(2:end-1) = 2*P1(2:end-1);
target_delta_distance_fft = P1;%FFT for delta distance from phase of target

Y = fft(target_amplitude-mean(target_amplitude),L_fft);
P2 = abs(Y/L_fft);
P1 = P2(1:L_fft/2+1);
P1(2:end-1) = 2*P1(2:end-1);
target_amplitude_fft = P1;%FFT of target reflection amplitude





figure(5)
subplot(1,2,1)
plot(f,target_amplitude_fft)
ylabel('Amplitude of tones in reflection amplitude [arb]')
xlabel('f [Hz]')

subplot(1,2,2)
plot(f,target_delta_distance_fft)
ylabel('Amplitudes of tones in reflection phase [m]')
xlabel('f [Hz]')


figure(6)
subplot(2,2,1)
plot(t,target_amplitude)
xlabel('t [s]')
ylabel('Amplitude of tracked target [arb]')

subplot(2,2,2)
plot(t,target_phase)
xlabel('t [s]')
ylabel('Phase of tracked target [rad]')

subplot(2,2,3)
plot(t,target_distance)
xlabel('t [s]')
ylabel('Distance of tracked target [m]')

subplot(2,2,4)
plot(t,5e-3/2/pi/2*(target_phase - mean(target_phase)))
xlabel('t [s]')
ylabel('Delta distance of tracked target [m]')


%Plot of IQ data

%{

figure(1)

figure(5)

figure(6)

figure(7)

figure(11)

figure(12)
figure(13)
%}
figure(5)
figure(6)